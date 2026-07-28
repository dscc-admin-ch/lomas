{
  perSystem =
    { self', pkgs, ... }:
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
          };
          shellHook = ''
            unset PYTHONPATH
            export REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
          '';
        };
      };
    };
}
