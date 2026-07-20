{ inputs, ... }:
{
  perSystem =
    { pkgs, ... }:
    let
      pyEnv = pkgs.callPackage ../devenv/lib.nix {
        inherit (inputs) pyproject-nix pyproject-build-systems uv2nix;
        workspaceRoot = ../.;
      };
    in
    {
      packages = {
        inherit (pyEnv)
          lomasEnv
          virtualenv
          lomasServerApp
          lomasClient
          ;
      };
    };
}
