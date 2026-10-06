{
  perSystem =
    {
      self',
      pkgs,
      lib,
      ...
    }:
    let
      inherit (import ./_dex.nix { inherit pkgs lib; }) dex-service;
      inherit (import ./_garage.nix { inherit pkgs lib; }) garage-service;

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
