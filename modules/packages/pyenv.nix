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
      # Build our python package & environments from local root (uv.lock)
      pyEnvs = lib.genAttrs' [ "12" "13" "14" ] (
        version:
        lib.nameValuePair ("py3${version}") (
          pkgs.callPackage ./_lib.nix {
            inherit (inputs) pyproject-nix pyproject-build-systems uv2nix;
            python3 = pkgs."python3${version}";
            workspaceRoot = ../../.;
          }
        )
      );
    in
    {
      packages = rec {
        # make loams python packages available
        lomasService = lomasService_3_14;
        lomasClient = lomasClient_3_14;
        lomasEnv = lomasEnv_3_14;
        lomasEnvDev = lomasEnvDev_3_14;

        lomasEnv_3_12 = pyEnvs.py312.lomasEnv;
        lomasEnvDev_3_12 = pyEnvs.py312.lomasEnvDev;
        lomasService_3_12 = pyEnvs.py312.lomasService;
        lomasClient_3_12 = pyEnvs.py312.lomasClient;
        lomasEnv_3_13 = pyEnvs.py313.lomasEnv;
        lomasEnvDev_3_13 = pyEnvs.py313.lomasEnvDev;
        lomasService_3_13 = pyEnvs.py313.lomasService;
        lomasClient_3_13 = pyEnvs.py313.lomasClient;
        lomasEnv_3_14 = pyEnvs.py314.lomasEnv;
        lomasEnvDev_3_14 = pyEnvs.py314.lomasEnvDev;
        lomasService_3_14 = pyEnvs.py314.lomasService;
        lomasClient_3_14 = pyEnvs.py314.lomasClient;

      };

      # add expose packages to (nix flake) check
      checks = lib.mapAttrs' (name: lib.nameValuePair "package-${name}") self'.packages;
    };
}
