{
  perSystem =
    {
      self',
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
          version = "0.6.0";
          units = [ dex-unit ];
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
        ];
        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = "${self'.packages."lomasEnvDev_3_${version}"}/bin/python";
          UV_PYTHON_DOWNLOADS = "never";
          # some editor uses this to find py sources
          VIRTUAL_ENV = ".devenv/profile";
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
          # doas portablectl reattach "$DEX/*.raw"
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
