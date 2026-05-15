{ inputs, ... }:
{
  perSystem =
    { system, pkgs, ... }:
    let
      cluster = inputs.kubenix.evalModules.${system} {
        module = {
          imports = [
            ../deploy/cluster.nix
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
      packages = {
        # kubectl apply -f $(nix eval --raw .#kubeConf)
        # kubeConf = cluster.config.kubernetes.result;

        # cluster = cluster;
      };
    };
}
