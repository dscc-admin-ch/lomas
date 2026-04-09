{
  kubenix,
  config,
  lib,
  ...
}:
let
  inherit (lib) mkOption types;
  inherit (config.kubernetes.helm.releases) lomas-dex;
  inherit (config.kubernetes.helm.releases) rabbitmq;
in
{
  imports = [
    kubenix.modules.k8s
    kubenix.modules.helm
    ./rabbit.nix
    ./dex.nix
    ./objstore.nix
  ];

  options = {
    namespace = mkOption {
      type = types.str;
      default = "default";
    };

    hostname = mkOption {
      type = types.str;
      default = "example.com";
    };

    oidc = {
      issuer = mkOption {
        type = types.str;
        default = "";
      };

      discoveryUrl = mkOption {
        type = types.str;
        default = "${config.oidc.issuer}/.well-known/openid-configuration";
      };

      dashboard = {
        client_id = mkOption { type = types.str; };
        client_secret = mkOption {
          type = types.nullOr types.str;
          default = null;
        };
        redirect_uri = mkOption { type = types.str; };
      };
    };

  };

  config = {
    kubenix.project = "lomas-nix";
    kubernetes.namespace = config.namespace;
    kubernetes.resources = {
      ingresses."${config.hostname}".spec = {
        ingressClassName = "onyxia";
        rules = [
          {
            host = config.hostname;
            http.paths = [
              {
                backend.service = {
                  name = "lomas";
                  port.number = 80;
                };
                path = "/";
                pathType = "Prefix";
              }
              {
                backend.service = {
                  name = "lomas-dashboard";
                  port.number = 80;
                };
                path = "/admin";
                pathType = "Prefix";
              }
            ];
          }
          {
            host = "auth-${config.hostname}";
            http.paths = [
              {
                backend.service = {
                  name = lomas-dex.name;
                  port.number = lomas-dex.values.service.ports.http.port;
                };
                path = "/";
                pathType = "Prefix";
              }
            ];
          }
        ];
      };

      configMaps = {
        dashboard-auth-config.data."secrets.toml" =
          let
            inherit (config.oidc.dashboard) client_id client_secret redirect_uri;
          in
          ''
            [auth]
            client_id = "${client_id}"
            client_secret = "${client_secret}"
            redirect_uri = "${redirect_uri}"
            server_metadata_url = "${config.oidc.discoveryUrl}"
            cookie_secret = "changeme"
            expose_tokens = [ "access", "id" ]
          '';
      };

      services.lomas.spec = {
        # selector.app = "lomas-dashboard";
        selector."app.kubernetes.io/instance" = "lomas";
        selector."app.kubernetes.io/name" = "lomas-server";

        ports = [
          {
            name = "http";
            port = 80;
            targetPort = 48080;
          }
        ];
      };
      deployments.lomas.spec = {
        replicas = 1;
        selector.matchLabels."app.kubernetes.io/instance" = "lomas";
        selector.matchLabels."app.kubernetes.io/name" = "lomas-server";
        template = {
          metadata.labels."app.kubernetes.io/instance" = "lomas";
          metadata.labels."app.kubernetes.io/name" = "lomas-server";
          spec = {
            containers.lomas = {
              image = "dsccadminch/lomas:sha-4c90599";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-serve" ];
              # volumeMounts = {
              #   "/persistent-storage".name = "data";
              # };
              env = lib.attrsToList (
                lib.mapAttrs (_: toString) {
                  LOMAS_SERVICE_PORT = 48080;
                  LOMAS_DEX_PORT = lomas-dex.values.service.ports.http.port; # 4445
                  LOMAS_RABBIT_MQ_PORT = rabbitmq.values.containerPorts.amqp; # 5672
                  LOMAS_RABBIT_MQ_MGMT_PORT = rabbitmq.values.containerPorts.manager; # 15672
                  LOMAS_RABBIT_MQ_USER = rabbitmq.values.auth.username; # "guest"
                  LOMAS_RABBIT_MQ_PASS = rabbitmq.values.auth.password; # "guest"
                  LOMAS_DASHBOARD_PORT = 8501;
                  LOMAS_MINIO_PORT = 19000;
                  LOMAS_MINIO_CONSOLE_PORT = 19001;
                  LOMAS_MINIO_ROOT_USER = "admin";
                  LOMAS_MINIO_ROOT_PWD = "admin123";
                  LOMAS_OTEL_PORT = 4317;
                  LOMAS_CLIENT_PORT = 8888;
                  LOMAS_SERVICE_authenticator__oidc_discovery_url = config.oidc.discoveryUrl;
                }
              );
            };
          };
        };
      };

      deployments.lomas-worker.spec = {
        replicas = 2;
        selector.matchLabels."app.kubernetes.io/instance" = "lomas";
        selector.matchLabels."app.kubernetes.io/name" = "lomas-worker";
        template = {
          metadata.labels."app.kubernetes.io/instance" = "lomas";
          metadata.labels."app.kubernetes.io/name" = "lomas-worker";
          spec = {
            containers.lomas = {
              image = "dsccadminch/lomas:sha-4c90599";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-work" ];
            };
          };
        };
      };

      services.lomas-dashboard.spec = {
        # selector.app = "lomas-dashboard";
        selector."app.kubernetes.io/instance" = "lomas";
        selector."app.kubernetes.io/name" = "dashboard";

        ports = [
          {
            name = "http";
            port = 80;
            targetPort = 8501;
          }
        ];
      };
      deployments.lomas-dashboard.spec = {
        replicas = 1;
        # selector.matchLabels.app = "lomas-dashboard";
        selector.matchLabels."app.kubernetes.io/instance" = "lomas";
        selector.matchLabels."app.kubernetes.io/name" = "dashboard";

        template = {
          # metadata.labels.app = "lomas-dashboard";
          metadata.labels."app.kubernetes.io/instance" = "lomas";
          metadata.labels."app.kubernetes.io/name" = "dashboard";

          spec = {
            containers.lomas = {
              image = "dsccadminch/lomas:sha-4c90599";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-dashboard" ];
              volumeMounts = {
                "/config".name = "config";
              };
              env = lib.attrsToList {
                LOMAS_ADMIN_SERVER_URL = "https://${config.hostname}";
                LOMAS_ADMIN_SERVER_SERVICE = "https://${config.hostname}";
                STREAMLIT_SECRETS_FILES = "/config/secrets.toml";
              };
            };
            volumes = {
              config.configMap.name = "dashboard-auth-config";
            };
          };
        };
      };

      jobs.lomas-demo-setup.spec = {
        template = {
          spec = {
            restartPolicy = "Never";
            initContainers.wait = {
              image = "dsccadminch/lomas:sha-4c90599";
              imagePullPolicy = "IfNotPresent";
              command = [ "/bin/bash" ];
              args = [
                "-c"
                ''
                  #!/usr/local/env bash
                  until [ $(curl -m 0.5 -fso /dev/null -w "%{http_code}" -k http://lomas/live) -eq 200 ]; do
                    echo "waiting for lomas"
                    sleep 2
                  done;
                ''
              ];
            };
            containers.lomas = {
              image = "dsccadminch/lomas:sha-4c90599";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-demo-setup" ];
              env = lib.attrsToList {
                LOMAS_ADMIN_SERVER_URL = "http://lomas";
                LOMAS_ADMIN_SERVER_SERVICE = "http://lomas";
                LOMAS_ADMIN_DEX_CONFIG__URL = "grpc://${lomas-dex.name}:${toString lomas-dex.values.service.ports.grpc.port}";
              };
            };
          };
        };
      };
    };

  };
}
