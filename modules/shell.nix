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
      makePyShell =
        version:
        pkgs.mkShellNoCC {
          packages = [
            self'.packages."lomasEnvDev_3_${version}"
            pkgs.uv
            pkgs.pre-commit
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
          '';
        };
    in
    {
      devShells = (lib.genAttrs' [ "12" "13" "14" ] (ver: lib.nameValuePair "py3${ver}" (makePyShell ver))) // {
        default = makePyShell "14";
      };

      # add shells to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "devShell-${name}") self'.devShells;
    };
}
