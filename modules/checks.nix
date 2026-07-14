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
              LOMAS_SERVICE_amqp__url = "amqp://rabbitmq:5672";
              LOMAS_SERVICE_amqp__username = "lomas_guest";
              LOMAS_SERVICE_amqp__password = "lomas_guest";
              LOMAS_SERVICE_authenticator__authentication_type = lib.mkDefault "free_pass";
            };
          };

          commonOdicContainers = {
            rabbitmq =
              { config, ... }:
              {
                imports = [ commonConfig ];
                networking.firewall.allowedTCPPorts = [
                  5672
                  15672
                ];
                services.rabbitmq = {
                  enable = true;
                  listenAddress = "0.0.0.0";
                  managementPlugin.enable = true;
                  configItems = {
                    default_user = config.environment.sessionVariables.LOMAS_SERVICE_amqp__username;
                    default_pass = config.environment.sessionVariables.LOMAS_SERVICE_amqp__password;
                    "deprecated_features.permit.transient_nonexcl_queues" = "false";
                    "deprecated_features.permit.management_metrics_collection" = "false";
                  };
                };
                systemd.services.rabbitmq.serviceConfig.Restart = lib.mkForce "no";
              };

            server = {
              imports = [ self.nixosModules.lomas ];
              services.lomas = {
                enable = true;
                port = 8080;
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
                amqpUrl = "amqp://rabbitmq:5672";
                amqpUsername = "lomas_guest";
                amqpPassword = "lomas_guest";
              };
            };

            worker1 = {
              imports = [ self.nixosModules.lomas ];
              services.lomas = {
                enable = true;
                workerOnly = true;
                amqpUrl = "amqp://rabbitmq:5672";
                amqpUsername = "lomas_guest";
                amqpPassword = "lomas_guest";
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
                # Local RabbitMQ
                services.rabbitmq = {
                  enable = true;
                  managementPlugin.enable = true;
                  configItems = {
                    default_user = "guest";
                    default_pass = "guest";
                    "deprecated_features.permit.transient_nonexcl_queues" = "false";
                    "deprecated_features.permit.management_metrics_collection" = "false";
                  };
                };
                systemd.services.rabbitmq.serviceConfig.Restart = lib.mkForce "no";

                services.lomas = {
                  enable = true;
                  workerOnly = true;
                  amqpUrl = "amqp://localhost:${toString config.services.rabbitmq.port}";
                  amqpUsername = config.services.rabbitmq.configItems.default_user;
                  amqpPassword = config.services.rabbitmq.configItems.default_pass;
                };
              };
            # https://nixos.org/manual/nixos/stable/index.html#ssec-machine-objects
            testScript = ''
              worker.start()

              worker.wait_for_unit("rabbitmq.service")
              worker.wait_for_open_port(15672)

              worker.start_job("lomas-worker@1")
              worker.wait_for_unit("lomas-worker@1.service")
            '';
          };

          "client-init" = pkgs.testers.runNixOSTest {
            name = "client-init";
            containers = commonOdicContainers // {
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

                rabbitmq.wait_for_unit("rabbitmq.service")
                rabbitmq.wait_for_open_port(15672)

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
                commonOdicContainers
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
                          datasets_list = [
                            {
                              dataset_name = "FSO_INCOME_SYNTHETIC";
                              initial_epsilon = 50;
                              initial_delta = 1;
                            }
                            {
                              dataset_name = "penguin";
                              initial_epsilon = 500;
                              initial_delta = 10;
                            }
                          ];
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
                      self'.packages.lomasServerApp
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
                      amqpUrl = "amqp://rabbitmq:5672";
                      amqpUsername = "lomas_guest";
                      amqpPassword = "lomas_guest";
                    };
                  };
                  worker3 = {
                    imports = [ self.nixosModules.lomas ];
                    services.lomas = {
                      enable = true;
                      workerOnly = true;
                      amqpUrl = "amqp://rabbitmq:5672";
                      amqpUsername = "lomas_guest";
                      amqpPassword = "lomas_guest";
                    };
                  };
                })
              ];

              testScript = ''
                start_all()

                rabbitmq.wait_for_unit("rabbitmq.service")
                rabbitmq.wait_for_open_port(15672)

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
