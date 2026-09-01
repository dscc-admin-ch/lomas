{ self, ... }:
{
  perSystem =
    {
      self',
      lib,
      pkgs,
      ...
    }:
    {
      checks =
        let
          commonConfig = {
            environment.sessionVariables = {
              LOMAS_SERVER_authenticator__authentication_type = lib.mkDefault "free_pass";
            };
          };

          commonOidcContainers = {
            server = {
              imports = [ self.nixosModules.lomas ];
              services.lomas = {
                enable = true;
                port = 8080;
                adminPort = 8081;
                openFirewall = true;
                listenAddress = "0.0.0.0";
                initUsers = lib.mkDefault ../server/data/collections/user_collection.yaml;
                initDatasets = lib.mkDefault (
                  builtins.toFile "dataset_collection.yaml" (
                    builtins.toJSON {
                      datasets = [
                        {
                          dataset_name = "PENGUIN";
                          dataset_access = {
                            database_type = "PATH_DB";
                            path = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv";
                          };
                          metadata_access = {
                            database_type = "PATH_DB";
                            path = ../server/data/collections/metadata/penguin_metadata.json;
                          };
                        }
                      ];
                    }
                  )
                );
              };
            };

            worker1 = {
              imports = [ self.nixosModules.lomas ];
              services.lomas = {
                enable = true;
                workerOnly = true;
              };
            };

            dex = {
              imports = [ commonConfig ];
              networking.firewall.allowedTCPPorts = [
                8080
                50051
              ];
              services.dex = {
                enable = true;
                settings = {
                  issuer = "http://dex:8080/dex";
                  web.http = "0.0.0.0:8080";
                  grpc.addr = "0.0.0.0:50051";
                  storage.type = "memory";
                  staticClients = [
                    {
                      id = "lomas_api";
                      public = false;
                      name = "lomas_api";
                      secret = "lomas_api";
                    }
                    {
                      id = "lomas_client";
                      public = true;
                      name = "lomas_client";
                      redirectURIs = [ "/device/callback" ];
                    }
                  ];
                  # Enable local users
                  enablePasswordDB = true;
                  # Allow password grants with local users
                  oauth2.passwordConnector = "local";
                };
              };
            };
          };
        in
        {
          "worker-start" = pkgs.testers.runNixOSTest {
            name = "worker";
            # Type checking on extra packages doesn't work yet
            # skipTypeCheck = true;
            containers.worker =
              { config, ... }:
              {
                imports = [ self.nixosModules.lomas ];
                services.lomas = {
                  enable = true;
                  workerOnly = true;
                };
              };
            # https://nixos.org/manual/nixos/stable/index.html#ssec-machine-objects
            testScript = ''
              worker.start()

              worker.start_job("lomas-worker@1")
              worker.wait_for_unit("lomas-worker@1.service")
            '';
          };

          "client-init" = pkgs.testers.runNixOSTest {
            name = "client-init";
            containers = commonOidcContainers // {
              # Client shoud work with nothing but the client package.
              client = {
                environment.systemPackages = [ self'.packages.lomasClient ];
              };
            };
            testScript =
              let
                clientScript = builtins.toFile "client_test.py" ''
                  from lomas_client import Client
                  from rich.pretty import pprint

                  client = Client(
                    app_url="http://server:8080",
                    dataset_name="PENGUIN",
                    oidc_discovery_url="http://dex:8080/dex/.well-known/openid-configuration",
                    use_password_flow=True,
                    user_name="dr.antartica@example.com",
                    user_password="dr.antartica",
                  )

                  metadata = client.get_dataset_metadata()
                  pprint(metadata)
                '';
              in
              ''
                start_all()

                server.wait_for_unit("lomas.service")

                worker1.start_job("lomas-worker@1")
                worker1.wait_for_unit("lomas-worker@1.service")

                dex.wait_for_unit("dex.service")

                client.succeed("python ${clientScript}")
              '';
          };

          "load" =
            let
              userParralel = {
                n = 10;
                max = 100;
              };
            in
            pkgs.testers.runNixOSTest {
              name = "load test";

              containers = lib.mkMerge [
                commonOidcContainers
                ({
                  server.services.lomas = {
                    initUsers = pkgs.writeText "users.yaml" (
                      builtins.toJSON {
                        users = builtins.genList (idx: {
                          id = {
                            name = "user-${toString idx}";
                            email = "user-${toString idx}@bench.com";
                            client_secret = "secret-${toString idx}";
                          };
                          may_query = true;
                          datasets = {
                            FSO_INCOME_SYNTHETIC = {
                              dataset_name = "FSO_INCOME_SYNTHETIC";
                              initial_budget = {
                                epsilon = 50;
                                delta = 1;
                              };
                            };
                            penguin = {
                              dataset_name = "penguin";
                              initial_budget = {
                                epsilon = 500;
                                delta = 10;
                              };
                            };
                          };
                        }) userParralel.max;
                      }
                    );
                    initDatasets = pkgs.writeText "datasets.yaml" (
                      builtins.toJSON {
                        datasets = [
                          {
                            dataset_name = "FSO_INCOME_SYNTHETIC";
                            dataset_access = {
                              database_type = "PATH_DB";
                              # https path won't do here are we can't assume general outside-world routing
                              path = pkgs.fetchurl {
                                url = "https://raw.githubusercontent.com/dscc-admin-ch/lomas/refs/heads/master/server/data/datasets/income_synthetic_data.csv";
                                hash = "sha256-I8b0qYsQfZR7UwM7k7pa97qFuyeV4haqjISUQvGR/+w=";
                              };
                              # When github is down ...
                              # path = ../server/lomas_server/tests/test_data/income_synthetic_data.csv;
                            };
                            metadata_access = {
                              database_type = "PATH_DB";
                              path = ../server/data/collections/metadata/fso_income_synthetic_metadata.json;
                            };
                          }
                          {
                            dataset_name = "penguin";
                            dataset_access = {
                              database_type = "PATH_DB";
                              path = ../server/lomas_server/tests/test_data/test_penguin.csv;
                            };
                            metadata_access = {
                              database_type = "PATH_DB";
                              path = ../server/data/collections/metadata/penguin_metadata.json;
                            };
                          }
                        ];
                      }
                    );
                  };
                })
                ({
                  bencher = {
                    imports = [ commonConfig ];
                    environment.systemPackages = [
                      self'.packages.lomasService
                      self'.packages.lomasClient
                    ];
                    environment.sessionVariables = {
                      LOMAS_CLIENT_OIDC_DISCOVERY_URL = "http://dex:8080/dex/.well-known/openid-configuration";
                      LOMAS_CLIENT_USE_PASSWORD_FLOW = "true";
                    };
                  };
                  # Add 2 workers
                  worker2 = {
                    imports = [ self.nixosModules.lomas ];
                    services.lomas = {
                      enable = true;
                      workerOnly = true;
                    };
                  };
                  worker3 = {
                    imports = [ self.nixosModules.lomas ];
                    services.lomas = {
                      enable = true;
                      workerOnly = true;
                    };
                  };
                })
              ];

              testScript = ''
                start_all()

                server.wait_for_unit("lomas.service")

                for worker in [worker1, worker2, worker3]:
                    service_name = f"lomas-worker@{worker.name[-1]}"
                    worker.start_job(service_name)
                    worker.wait_for_unit(service_name)

                dex.wait_for_unit("dex.service")

                # benchme
                bencher.succeed("lomas-bench -h")
                bencher.succeed("${pkgs.parallel}/bin/parallel lomas-bench --idx {} -s 'http://server:8080' -d FSO_INCOME_SYNTHETIC  ::: $(seq ${toString userParralel.n})")
              '';
            };

        };
    };
}
