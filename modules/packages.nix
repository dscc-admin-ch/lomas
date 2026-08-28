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
      # Eval our defaults (as options) and get the resulting config
      inherit ((lib.evalModules { modules = [ ./_defaults.nix ]; }).config) ports;

      # Build our python package & environments from local root (uv.lock)
      pyEnv = pkgs.callPackage ../devenv/lib.nix {
        inherit (inputs) pyproject-nix pyproject-build-systems uv2nix;
        workspaceRoot = ../.;
      };

      workingDir = "/data";
      LOMAS_ADMIN_USER_YAML = "${workingDir}/collections/user_collection.yaml";
      LOMAS_ADMIN_DATASET_YAML = "${workingDir}/collections/dataset_collection.yaml";
    in
    {
      # add expose packages to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "package-${name}") self'.packages;

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
              tini
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
            install -Dm 644 ${../server/data/collections/user_collection.yaml} ${lib.removePrefix "/" LOMAS_ADMIN_USER_YAML}
            install -Dm 644 ${../server/data/collections/dataset_collection.yaml} ${lib.removePrefix "/" LOMAS_ADMIN_DATASET_YAML}

            install -dm 755 data/collections/
            cp -r --no-preserve=all ${../server/data/collections}/metadata data/collections/
            install -dm 755 data/datasets/
            cp -r --no-preserve=all ${../server/data/datasets/covid_synthetic_data.csv} data/datasets/covid_synthetic_data.csv
          '';
          config = {
            Entrypoint = [
              "${pkgs.tini}/bin/tini"
              "-g"
              "--"
            ];
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
            Entrypoint = [
              "${pkgs.tini}/bin/tini"
              "-g"
              "--"
            ];
            Cmd = [
              "lomas"
              "start"
            ];
            Env = lib.mapAttrsToList (name: value: "${name}=${toString value}") {
              LOMAS_SERVER_host_ip = "0.0.0.0";
              LOMAS_SERVER_user_host_port = ports.lomas.userApiService;
              LOMAS_SERVER_admin_host_port = ports.lomas.adminApiService;
              LOMAS_SERVER_bootstrap = "deadbeef";
              LOMAS_SERVER_data_directory = workingDir;
              # LOMAS_SERVER_database_directory="/tmp/lomas-db/";
              LOMAS_SERVER_authenticator__authentication_type = "oidc";
              LOMAS_SERVER_authenticator__oidc_discovery_url = "http://dex:${ports.lomas.dex.api}/dex/.well-known/openid-configuration";
              LOMAS_SERVER_telemetry__collector_endpoint = "http://otel-collector:${ports.otlp.grpc}";
              LOMAS_CLIENT_APP_URL = "http://lomas_server:${ports.lomas.userApiService}";
              LOMAS_CLIENT_OIDC_DISCOVERY_URL = "http://dex:${ports.lomas.dex.api}/dex/.well-known/openid-configuration";
              LOMAS_CLIENT_USE_PASSWORD_FLOW = true;
              LOMAS_CLIENT_telemetry__collector_endpoint = "http://otel-collector:${ports.otlp.grpc}";
              inherit LOMAS_ADMIN_USER_YAML LOMAS_ADMIN_DATASET_YAML;
              LOMAS_ADMIN_DEX_CONFIG__URL = "http://dex:${ports.lomas.dex.admin}";
              LOMAS_ADMIN_server_url = "http://lomas_server:${ports.lomas.adminApiService}";
              LOMAS_ADMIN_BOOTSTRAP = "deadbeef";
              STREAMLIT_BROWSER_GATHER_USAGE_STATS = 0;
              STREAMLIT_SERVER_PORT = ports.streamlit;
              STREAMLIT_SERVER_BASE_URL_PATH = "/admin";
              STREAMLIT_SERVER_HEADLESS = 1;
            };
            ExposedPorts = lib.genAttrs [
              ports.lomas.userApiService
              ports.lomas.adminApiService
              ports.streamlit
              ports.jupyter
            ] (lib.const { });
            Volumes = {
              "${workingDir}/collections" = { };
              "${workingDir}/datasets" = { };
            };
          };
        };
      };
    };
}
