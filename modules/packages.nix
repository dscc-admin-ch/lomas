{ inputs, ... }:
{
  perSystem =
    {
      self',
      pkgs,
      lib,
      ...
    }:
    let
      inherit (lib.strings) removePrefix;

      pyEnv = pkgs.callPackage ../devenv/lib.nix {
        inherit (inputs) pyproject-nix pyproject-build-systems uv2nix;
        workspaceRoot = ../.;
      };

      workingDir = "/data";
      servicePort = "8080";
      LOMAS_ADMIN_USER_YAML = "${workingDir}/collections/user_collection.yaml";
      LOMAS_ADMIN_DATASET_YAML = "${workingDir}/collections/dataset_collection.yaml";
    in
    {
      packages = {
        # make loams python packages available
        inherit (pyEnv)
          lomasEnv
          lomasEnvDev
          lomasService
          lomasClient
          ;

        ##############################
        # OCI-docker images for RHOS #
        ##############################

        lomas-oci-raw = pkgs.dockerTools.buildLayeredImage {
          name = "lomas-oci-raw";
          tag = "latest";
          contents = builtins.attrValues {
            inherit (pkgs.dockerTools) binSh usrBinEnv caCertificates;
            inherit (pkgs)
              bashInteractive
              coreutils-full
              dnsutils
              wget
              curl
              which
              file
              bind
              git
              ;
            inherit (pyEnv) lomasEnv;
            lomas-dashboard = (
              pkgs.writeShellScriptBin "lomas-dashboard" ''
                cd ${pyEnv.lomasEnv}/lib/python*/site-packages/
                streamlit run lomas-server/administration/dashboard/about.py
              ''
            );
          };
          extraCommands = ''
            install -dm 1777 tmp
            install -Dm 644 ${../server/data/collections/user_collection.yaml} ${removePrefix "/" LOMAS_ADMIN_USER_YAML}
            install -Dm 644 ${../server/data/collections/dataset_collection.yaml} ${removePrefix "/" LOMAS_ADMIN_DATASET_YAML}

            install -dm 755 data/collections/
            cp -r --no-preserve=all ${../server/data/collections}/metadata data/collections/
            install -dm 755 data/datasets/
            cp -r --no-preserve=all ${../server/data/datasets/covid_synthetic_data.csv} data/datasets/covid_synthetic_data.csv
          '';
          config = {
            Cmd = [
              "lomas"
              "start"
            ];
            Env = lib.mapAttrsToList (name: value: "${name}=${toString value}") {
              inherit LOMAS_ADMIN_USER_YAML LOMAS_ADMIN_DATASET_YAML;
            };
            Volumes = {
              "/data/collections" = { };
              "/data/datasets" = { };
            };
          };
          maxLayers = 2;
        };

        lomas-oci = pkgs.dockerTools.buildLayeredImage {
          name = "lomas-oci";
          tag = "latest";
          fromImage = self'.packages.lomas-oci-raw;
          config = {
            Cmd = [
              "lomas"
              "start"
            ];
            Env = lib.mapAttrsToList (name: value: "${name}=${toString value}") {
              LOMAS_SERVICE_server__host_ip = "0.0.0.0";
              LOMAS_SERVICE_server__host_port = servicePort;
              LOMAS_SERVICE_bootstrap = "deadbeef";
              LOMAS_SERVICE_data_directory = workingDir;
              # LOMAS_SERVICE_database_directory="/tmp/lomas-db/";
              LOMAS_SERVICE_amqp__url = "amqp://rabbitmq:5672";
              LOMAS_SERVICE_amqp__username = "lomas_guest";
              LOMAS_SERVICE_amqp__password = "lomas_guest";
              LOMAS_SERVICE_authenticator__authentication_type = "oidc";
              LOMAS_SERVICE_authenticator__oidc_discovery_url = "http://dex:4445/dex/.well-known/openid-configuration";
              LOMAS_SERVICE_telemetry__collector_endpoint = "http://otel-collector:4317";
              LOMAS_CLIENT_APP_URL = "http://lomas_server:${servicePort}";
              LOMAS_CLIENT_OIDC_DISCOVERY_URL = "http://dex:4445/dex/.well-known/openid-configuration";
              LOMAS_CLIENT_USE_PASSWORD_FLOW = true;
              LOMAS_CLIENT_telemetry__collector_endpoint = "http://otel-collector:4317";
              inherit LOMAS_ADMIN_USER_YAML LOMAS_ADMIN_DATASET_YAML;
              LOMAS_ADMIN_DEX_CONFIG__URL = "http://dex:4446";
              LOMAS_ADMIN_server_url = "http://lomas_server:${servicePort}";
              LOMAS_ADMIN_BOOTSTRAP = "deadbeef";
              STREAMLIT_BROWSER_GATHER_USAGE_STATS = 0;
              STREAMLIT_SERVER_PORT = 8501;
              STREAMLIT_SERVER_BASE_URL_PATH = "/admin";
              STREAMLIT_SERVER_HEADLESS = 1;
            };
            ExposedPorts = {
              servicePort = { };
              "8888" = { };
              "8501" = { };
            };
            Volumes = {
              "${workingDir}/collections" = { };
              "${workingDir}/datasets" = { };
            };
          };
        };
      };
    };
}
