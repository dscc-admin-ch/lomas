{
  kubenix,
  config,
  lib,
  ...
}:
let
  inherit (lib) mkOption types;
in
{
  imports = [
    kubenix.modules.k8s
    kubenix.modules.helm
    ./rabbit.nix
    ./objstore.nix
    ./dex.nix
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
                  name = "lomas-dex";
                  port.number = 4445;
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
              image = "dsccadminch/lomas:sha-4b4bdbb";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-serve" ];
              # volumeMounts = {
              #   "/persistent-storage".name = "data";
              # };
              env = lib.attrsToList (
                lib.mapAttrs (_: toString) {
                  LOMAS_SERVICE_PORT = 48080;
                  LOMAS_DEX_PORT = 4445;
                  LOMAS_RABBIT_MQ_PORT = 5672;
                  LOMAS_RABBIT_MQ_MGMT_PORT = 15672;
                  LOMAS_RABBIT_MQ_USER = "guest";
                  LOMAS_RABBIT_MQ_PASS = "guest";
                  LOMAS_DASHBOARD_PORT = 8501;
                  LOMAS_MINIO_PORT = 19000;
                  LOMAS_MINIO_CONSOLE_PORT = 19001;
                  LOMAS_MINIO_ROOT_USER = "admin";
                  LOMAS_MINIO_ROOT_PWD = "admin123";
                  LOMAS_OTEL_PORT = 4317;
                  LOMAS_CLIENT_PORT = 8888;
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
              image = "dsccadminch/lomas:sha-4b4bdbb";
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
              image = "dsccadminch/lomas:sha-4b4bdbb";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-dashboard" ];
              volumeMounts = {
                "/config".name = "config";
              };
              env = lib.attrsToList {
                LOMAS_ADMIN_SERVER_URL = "https://${config.hostname}/dashboard";
                LOMAS_ADMIN_SERVER_SERVICE = "https://${config.hostname}/dashboard";
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
            containers.lomas = {
              image = "dsccadminch/lomas:sha-4b4bdbb";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-demo-setup" ];
              env = lib.attrsToList {
                LOMAS_ADMIN_SERVER_URL = "http://lomas";
                LOMAS_ADMIN_SERVER_SERVICE = "http://lomas";
                LOMAS_ADMIN_DEX_CONFIG__URL = "http://lomas-dex:5557";
              };
            };
          };
        };
      };
    };

  };
}
