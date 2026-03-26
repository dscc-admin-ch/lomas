{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    kubenix = {
      url = "github:hall/kubenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-kube-generators.url = "github:farcaller/nix-kube-generators";
  };

  outputs =
    {
      self,
      kubenix,
      nix-kube-generators,
      ...
    }@inputs:
    let
      system = "x86_64-linux";
      pkgs = kubenix.inputs.nixpkgs.legacyPackages.${system}.pkgs;
      cluster = kubenix.evalModules.${system} {
        module = {
          imports = [
            ./deploy/cluster.nix
            ({
              namespace = "user-bstuder";
              hostname = "caddy.user.lab.sspcloud.fr";
            })
          ];
        };
      };
      kubelib = nix-kube-generators.lib { inherit pkgs; };
    in
    {
      packages.${system} = {
        # nix build .
        default = cluster.config.kubernetes.result;

        # nix eval --json .#kubeConf | kubectl apply -f -
        kubeConf = cluster.config.kubernetes.generated;

        kubenix = kubenix.packages.${system}.default.override {
          module = import ./deploy/cluster.nix;
        };

        # get lomas server chart as attrset
        # nix eval --json .#serverChart
        serverChart = kubelib.fromHelm {
          name = "lomas-server";
          chart = ./server/deploy/helm/charts/lomas_server;
          namespace = "default";
        };
      };
    };
}
