{
  perSystem =
    {
      self',
      pkgs,
      lib,
      ...
    }:
    let
      makePyShell =
        version:
        pkgs.mkShell {
          packages = [
            self'.packages."lomasEnvDev_3_${version}"
            pkgs.uv
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
          '';
        };
    in
    {
      devShells = (lib.genAttrs' [ "12" "13" "14" ] (ver: lib.nameValuePair ("py3${ver}") (makePyShell ver))) // {
        default = makePyShell "14";
      };

      # add shells to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "devShell-${name}") self'.devShells;
    };
}
