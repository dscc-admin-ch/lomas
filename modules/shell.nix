{
  perSystem =
    {
      self',
      pkgs,
      lib,
      ...
    }:
    {
      devShells = {
        default = pkgs.mkShell {
          packages = [
            self'.packages.lomasEnvDev
            pkgs.uv
          ];
          env = {
            UV_NO_SYNC = "1";
            UV_PYTHON = "${self'.packages.lomasEnvDev}/bin/python";
            UV_PYTHON_DOWNLOADS = "never";
            # some editor uses this to find py sources
            VIRTUAL_ENV = ".devenv/profile";
          };
          shellHook = ''
            unset PYTHONPATH
            export REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
          '';
        };
      };

      # add shells to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "devShell-${name}") self'.devShells;
    };
}
