{
  perSystem =
    {
      self',
      config,
      pkgs,
      lib,
      ...
    }:
    let
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
          self'.packages.dex-service
          self'.packages.garage-service
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
          LOMAS_SERVER_authenticator__oidc_discovery_url = config.dev.dex.discoveryUrl;
          LOMAS_ADMIN_bootstrap = "deadbeef";
          LOMAS_ADMIN_external_url = "http://localhost:48081";
          # LOMAS_ADMIN_user_yaml = "${admin_data_dir}/collections/user_collection.yaml";
          # LOMAS_ADMIN_dataset_yaml = "${admin_data_dir}/collections/dataset_collection_devenv.yaml";
          LOMAS_ADMIN_dex_config__url = config.dev.dex.grpcUrl;
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

          export DEX=${self'.packages.dex-service}
          export GARAGE=${self'.packages.garage-service}
          # doas portablectl reattach "$DEX/*.raw"
          # doas portablectl reattach "$GARAGE/*.raw"
        '';
      };
    in
    {
      dev = {
        dex = {
          host = "localhost";
          address = "127.0.0.1";
          adminAddress = "127.0.0.1";
          oidc.clients = {
            apiServer = {
              client_id = "lomas_api";
              client_secret = "lomas_api";
            };
            apiClient = "lomas_client";
            adminDashboard = {
              client_id = "lomas_dashboard";
              client_secret = "lomas_dashboard";
              # todo: dashboard conf
              redirect_uri = "http://localhost:8501/admin/oauth2callback";
            };
            grafanaDashboard = {
              client_id = "lomas_grafana";
              client_secret = "lomas_grafana";
              # todo: grafana conf
              redirect_uri = "http://localhost:3000/login/generic_oauth";
            };
          };
        };

        garage = {
          # GK + 12 hex-encoded bytes
          keyId = "GK0123456789abcdefdeadbeef";
          # 32 hex-encoded bytes
          secretKey = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
          initFilesCopy = [
            {
              src = builtins.path {
                name = "penguinData";
                path = ../../server/lomas_server/tests/test_data/test_penguin.csv;
              };
              dst = "/data/test_penguin.csv";
            }
            {
              src = builtins.path {
                name = "penguinMetadata";
                path = ../../server/lomas_server/tests/test_data/metadata/penguin_metadata.json;
              };
              dst = "/metadata/penguin_metadata.json";
            }
            {
              src = builtins.path {
                name = "Titanic";
                path = ../../server/data/datasets/titanic.csv;
              };
              dst = "/data/titanic.csv";
            }
            {
              src = builtins.path {
                name = "TitanicMetadata";
                path = ../../server/data/collections/metadata/titanic_metadata.json;
              };
              dst = "/metadata/titanic_metadata.json";
            }
          ];
        };
      };

      make-shells = (lib.genAttrs' [ "12" "13" "14" ] (ver: lib.nameValuePair "py3${ver}" (makePyShell ver))) // {
        default = makePyShell "14";
      };

      # add shells to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "devShell-${name}") self'.devShells;
    };
}
