{
  kubenix,
  config,
  lib,
  ...
}:
{
  imports = [
    kubenix.modules.k8s
    kubenix.modules.helm
    ./rabbit.nix
    ./objstore.nix
  ];

  options = {
    namespace = lib.mkOption {
      type = lib.types.str;
      default = "default";
    };
    hostname = lib.mkOption {
      type = lib.types.str;
      default = "example.com";
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
            host = "${config.hostname}";
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
        ];
      };

      configMaps = {
        server-config.data."dex-config.yaml" = ''
          web:
            http: 0.0.0.0:4445

          storage:
            type: sqlite3
            config:
              file: /var/dex/dex.db

          grpc:
            addr: 0.0.0.0:4446

          # Enable local users
          enablePasswordDB: true
          # Allow password grants with local users
          oauth2:
            passwordConnector: local

          staticClients:
            # lomas api server
            - id: lomas_api
              public: false
              name: lomas_api
              secret: lomas_api
            # lomas client lib
            - id: lomas_client
              public: true
              name: lomas_client
              redirectURIs:
                # Enables device auth flow
                - '/device/callback'
            # lomas dashboard
            - id: lomas_dashboard
              public: false
              name: lomas_dashboard
              secret: lomas_dashboard
              redirectURIs:
                - http://localhost:8501/oauth2callback
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
            targetPort = 8080;
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
              image = "dsccadminch/lomas:sha-b01e287";
              imagePullPolicy = "IfNotPresent";
              command = [ "lomas-server" ];
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
              image = "dsccadminch/lomas:sha-b01e287";
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
            containers.lomas-server = {
              image = "dsccadminch/lomas:sha-b01e287";
              imagePullPolicy = "IfNotPresent";
              # volumeMounts = {
              #   "/persistent-storage".name = "data";
              # };
              env = lib.attrsToList {
                LOMAS_ADMIN_PATH_PREFIX = "/data";
                LOMAS_ADMIN_USER_YAML = "/collections/user_collection.yaml";
                LOMAS_ADMIN_DATASET_YAML = "/collections/dataset_collection.yaml";
                LOMAS_ADMIN_SERVER_URL = "https://${config.hostname}/dashboard";
                LOMAS_ADMIN_SERVER_SERVICE = "https://${config.hostname}/dashboard";
              };
            };
            volumes = {
              # config.configMap.name = "dashboard-server-config";
              # data.persistentVolumeClaim = {
              #   claimName = "lomas-server";
              # };
            };
          };
        };
      };
    };

  };
}
