{
  perSystem =
    {
      self',
      pkgs,
      lib,
      ...
    }:
    let
      inherit (lib.strings) hasPrefix substring stringLength;
      stripPath = strPath: if (hasPrefix "/" strPath) then (substring 1 (stringLength strPath) strPath) else strPath;

      admin_data_dir = "./server/data";

      # TODO: this should take config from treesitter
      pre-commit-config = pkgs.writeText "pre-commit-config.yaml" (
        builtins.toJSON {
          default_stages = [ "pre-commit" ];
          repos = [
            {
              repo = "local";
              hooks = [
                {
                  id = "nbstripout";
                  name = "nbstripout";
                  entry = "${lib.getExe pkgs.nbstripout}";
                  args = [
                    "--keep-output"
                    "--drop-empty-cells"
                  ];
                  files = "\\.ipynb$";
                  language = "unsupported";
                  stages = [ "pre-commit" ];
                }
                {
                  id = "nixfmt";
                  name = "nixfmt";
                  entry = "${lib.getExe pkgs.nixfmt}";
                  args = [
                    "--width"
                    "120"
                  ];
                  files = "\\.nix$";
                  language = "unsupported";
                  stages = [ "pre-commit" ];
                }
                {
                  id = "ruff-format";
                  name = "ruff-format";
                  entry = "${lib.getExe pkgs.ruff}";
                  args = [ "format" ];
                  language = "unsupported";
                  pass_filenames = false;
                  stages = [ "pre-commit" ];
                  types = [ "python" ];
                }
                {
                  id = "ruff";
                  name = "ruff";
                  entry = "${lib.getExe pkgs.ruff}";
                  args = [
                    "check"
                    "--fix"
                  ];
                  language = "unsupported";
                  pass_filenames = false;
                  stages = [ "pre-commit" ];
                  types = [ "python" ];
                }
              ];
            }
          ];
        }
      );

      build-docs = pkgs.writeShellApplication {
        name = "build-docs";
        runtimeInputs = [ self'.packages.lomasEnvDev ];
        runtimeEnv.NO_MKDOCS_2_WARNING = 1;
        text = ''
          mkdocs build
        '';
      };

      build-docs-local = pkgs.writeShellApplication {
        name = "build-docs-local";
        runtimeInputs = [ self'.packages.lomasEnvDev ];
        runtimeEnv.NO_MKDOCS_2_WARNING = 1;
        text = ''
          mkdocs serve -o
        '';
      };

      py-build = pkgs.writeShellApplication {
        name = "py-build";
        runtimeInputs = [ self'.packages.lomasEnvDev ];
        text = ''
          uv build --sdist core
          uv build --sdist client
          uv build --sdist server
        '';
      };

      dex-service =
        let
          dexConfig = pkgs.writeText "dex-config.yaml" ''
            issuer: http://localhost:4445/dex
            web:
              http: 127.0.0.1:4445
            storage:
              type: memory
            grpc:
              addr: 127.0.0.1:4446
            enablePasswordDB: true
            oauth2:
              passwordConnector: local
            expiry:
              deviceRequests: "5m"
              signingKeys: "6h"
              idTokens: "3s"         # Set very short for testing
              refreshTokens:
                disableRotation: false
                reuseInterval: "3s"
                validIfNotUsedFor: "24h" # "2160h" # 90 days
                absoluteLifetime: "3960h" # 165 days
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
                  - "/device/callback"
              # lomas dashboard
              - id: lomas_dashboard
                public: false
                name: lomas_dashboard
                secret: lomas_dashboard
                redirectURIs:
                  - http://localhost:8501/admin/oauth2callback
              # lomas grafana
              - id: lomas_grafana
                public: false
                name: lomas_grafana
                secret: lomas_grafana
                redirectURIs:
                  - http://localhost:3000/login/generic_oauth
            # Beware: static passwords cannot be deleted in dex.
            staticPasswords:
          '';

          dex-unit = pkgs.writeText "dex.service" ''
            [Unit]
            Description=Identity service OpenID Connect
            Documentation=https://dexidp.io/docs/

            [Service]
            Type=simple
            ExecStart=${lib.getExe pkgs.dex-oidc} serve ${dexConfig}
            TimeoutStopSec=2
          '';
        in
        pkgs.portableService {
          pname = "dex";
          version = "1";
          units = [ dex-unit ];
        };

      garage-service =
        let
          bucketName = "bucket";
          # GK + 12 hex-encoded bytes
          keyId = "GK0123456789abcdefdeadbeef";
          # 32 hex-encoded bytes
          secretKey = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
          serviceHost = "mygarage";
          port = 3900;
          apiPort = 3903;
          initFilesCopy = [
            {
              src = builtins.path {
                name = "penguinData";
                path = ../server/lomas_server/tests/test_data/test_penguin.csv;
              };
              dst = "/data/test_penguin.csv";
            }
            {
              src = builtins.path {
                name = "penguinMetadata";
                path = ../server/lomas_server/tests/test_data/metadata/penguin_metadata.json;
              };
              dst = "/metadata/penguin_metadata.json";
            }
            {
              src = builtins.path {
                name = "Titanic";
                path = ../server/data/datasets/titanic.csv;
              };
              dst = "/data/titanic.csv";
            }
            {
              src = builtins.path {
                name = "TitanicMetadata";
                path = ../server/data/collections/metadata/titanic_metadata.json;
              };
              dst = "/metadata/titanic_metadata.json";
            }
          ];
          format = pkgs.formats.toml { };
          settings = {
            metadata_dir = "/var/tmp/garage/meta";
            data_dir = "/var/tmp/garage/data";
            db_engine = "lmdb";

            replication_factor = 1;

            rpc_bind_addr = "[::]:3901";
            rpc_public_addr = "127.0.0.1:3901";
            rpc_secret = "00ae3c92972e91116f2612fb96ab64c963c2f7b163cab376569ec3e9be179d2d";

            s3_api = {
              s3_region = "us-east-1";
              api_bind_addr = "0.0.0.0:3900";
            };

            admin = {
              api_bind_addr = "0.0.0.0:${toString apiPort}";
              admin_token = "e3640a659b59c6a6b06c0820a2bd0380aa12124b61000aee7af684d10aab7fa0";
            };

            metrics_require_token = true;
            metrics_token = "ddd02920a2431ad2d8fb77207f2933e775873c2461894a443c61776a3db854fd";
          };
          garageConfig = format.generate "garage.toml" settings;
          garageInit = pkgs.writeShellApplication {
            name = "garage-init";
            runtimeInputs = [
              pkgs.coreutils # sleep
              pkgs.gnugrep
              pkgs.curl
              pkgs.jq
              pkgs.getent # hidden minio req
              pkgs.minio-client
              pkgs.garage_2
            ];
            runtimeEnv = { };
            text = ''
              function garageHealthEndpoint() {
                curl -f -H 'Authorization: Bearer ${settings.admin.admin_token}' \
                  'http://0.0.0.0:${toString apiPort}/v1/health' 2>/dev/null
              }

              GARAGE="garage -c ${garageConfig}"

              until garageHealthEndpoint; do
                echo "Garage not ready, waiting..."
                sleep 1
              done

              echo "Garage ready."
              echo "Configuring layout ..."
              # Apply the cluster layout once. Garage rejects S3 traffic until at
              # least one node has a role, so this step is mandatory before the
              # buckets can be touched.
              if $GARAGE status 2>/dev/null | grep -q "NO ROLE ASSIGNED"; then
                NODE_ID=$($GARAGE node id 2>/dev/null | cut -d@ -f1)
                $GARAGE layout assign -z dc1 -c 1G "$NODE_ID"
                $GARAGE layout apply --version 1
              fi

              if ! $GARAGE bucket info ${bucketName} > /dev/null; then
                $GARAGE bucket create ${bucketName}
              else
                echo "${bucketName} present"
              fi

              # $GARAGE key create bucket-key
              # $GARAGE bucket allow --read --write ${bucketName} --key bucket-key

              if ! $GARAGE key info ${keyId} > /dev/null; then
                $GARAGE key import --yes ${keyId} ${secretKey}
              else
                echo "${keyId} present"
              fi

              if ! ($GARAGE json-api GetBucketInfo '{"globalAlias": "${bucketName}"}' | jq '.keys[].accessKeyId' | grep -q ${keyId}); then
                $GARAGE bucket allow --read --write ${bucketName} --key ${keyId}
              else
                echo "${keyId} already has RW on ${bucketName}"
              fi

              # mini-client is absolute garbage (-C/--config-dir still requires $HOME)
              HOME=/var/tmp/mc mc alias set ${serviceHost} http://localhost:${toString port} ${keyId} ${secretKey} --api S3v4
              ${lib.strings.concatLines (
                (map (attrs: "HOME=/var/tmp/mc mc cp ${attrs.src} ${serviceHost}/${bucketName}/${stripPath attrs.dst}") initFilesCopy)
                ++ [ "HOME=/var/tmp/mc mc ls --recursive --versions ${serviceHost}/${bucketName}" ]
              )}
            '';
          };
          garage-unit = pkgs.writeText "garage.service" ''
            [Unit]
            Description=S3 object store
            Documentation=https://garagehq.deuxfleurs.fr/documentation

            [Service]
            Type=simple
            # Share /tmp, /var/tmp with host
            PrivateTmp=true
            ExecStart=${lib.getExe pkgs.garage_2} -c ${garageConfig} server
            ExecStartPost=${lib.getExe garageInit}
          '';
        in
        pkgs.portableService {
          pname = "garage";
          version = "1";
          units = [ garage-unit ];
        };

      # https://github.com/nicknovitski/make-shell/blob/main/SHELL_MODULES.md
      makePyShell = version: {
        imports = [ ];
        packages = [
          self'.packages."lomasEnvDev_3_${version}"
          pkgs.uv
          pkgs.pre-commit
          build-docs
          build-docs-local
          py-build
          dex-service
          garage-service
        ];
        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = "${self'.packages."lomasEnvDev_3_${version}"}/bin/python";
          UV_PYTHON_DOWNLOADS = "never";
          # some editor uses this to find py sources
          VIRTUAL_ENV = ".devenv/profile";

          # lomas
          LOMAS_SERVER_worker_api_key = "workerdeadbeef";
          LOMAS_SERVER_authenticator__authentication_type = "oidc";
          LOMAS_SERVER_authenticator__oidc_discovery_url = "http://localhost:4445/dex/.well-known/openid-configuration";
          LOMAS_ADMIN_bootstrap = "deadbeef";
          LOMAS_ADMIN_external_url = "http://localhost:48081";
          # LOMAS_ADMIN_user_yaml = "${admin_data_dir}/collections/user_collection.yaml";
          # LOMAS_ADMIN_dataset_yaml = "${admin_data_dir}/collections/dataset_collection_devenv.yaml";
          LOMAS_ADMIN_dex_config__url = "grpc://localhost:4446";
          LOMAS_CLIENT_use_password_flow = true;
        };
        shellHook = ''
          unset PYTHONPATH
          export REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")

          # Pre-commit
          preCommitFile=.pre-commit-config.yaml
          if ! ([ -e "$preCommitFile" ] && [ $(nix hash file "$preCommitFile") = $(nix hash file ${pre-commit-config}) ]); then
            ln -sf ${pre-commit-config} "$preCommitFile"
            pre-commit install --install-hooks
          fi

          export DEX=${dex-service}
          export GARAGE=${garage-service}
          # doas portablectl reattach "$DEX/*.raw"
          # doas portablectl reattach "$GARAGE/*.raw"
        '';
      };
    in
    {
      make-shells = (lib.genAttrs' [ "12" "13" "14" ] (ver: lib.nameValuePair "py3${ver}" (makePyShell ver))) // {
        default = makePyShell "14";
      };

      # add shells to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "devShell-${name}") self'.devShells;
    };
}
