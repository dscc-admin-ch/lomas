{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    kubenix = {
      url = "github:hall/kubenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      kubenix,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }@inputs:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system}.pkgs;
      lib = pkgs.lib;
      cluster = kubenix.evalModules.${system} {
        module = {
          imports = [
            ./deploy/cluster.nix
            (rec {
              namespace = "user-bstuder";
              hostname = "lomasbs.lab.sspcloud.fr";
              oidc = {
                issuer = "http://auth-${hostname}";
                dashboard = {
                  client_id = "lomas_dashboard";
                  client_secret = "lomas_dashboard";
                  # tricky https here ?
                  redirect_uri = "https://${hostname}/admin/oauth2callback";
                };
              };
            })
          ];
        };
      };
    in
    {
      packages.${system} = {
        # nix build .
        default = cluster.config.kubernetes.result;

        # nix eval --json .#kubeConf | kubectl apply -f -
        kubeConf = cluster.config.kubernetes.generated;

        cluster = cluster;
      };

      devShells.${system} =
        let
          pyEnv = import ./devenv/lib.nix {
            inherit
              pkgs
              lib
              uv2nix
              pyproject-nix
              pyproject-build-systems
              ;
            workspaceRoot = ./.;
          };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pyEnv.virtualenv
              pkgs.uv
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pyEnv.pythonSet.python.interpreter;
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
