{ config, kubenix, ... }:
let
  inherit (config.oidc) dashboard;
in
{
  kubernetes.helm.releases.lomas-dex = {
    chart = kubenix.lib.helm.fetch {
      repo = "https://charts.dexidp.io";
      chart = "dex";
      version = "0.24.0";
      sha256 = "sha256-uwrCJ9cReOQlvJ0+zciHA387l049Q4HP7atU0xqpE4o=";
    };

    namespace = config.namespace;

    values = {
      ingress.enabled = false;
      rbac.create = false;
      serviceAccount.create = false;
      grpc.enabled = true;
      service.ports = {
        http.port = 4445;
        grcp.port = 4446;
      };
      config = {
        issuer = config.oidc.issuer;
        storage.type = "memory";
        enablePasswordDB = true;
        oauth2.passwordConnector = "local";
        staticClients = [
          {
            id = "lomas_api";
            public = false;
            name = "lomas_api";
            secret = "lomas_api";
          }
          {
            id = "lomas_client";
            public = true;
            name = "lomas_client";
            redirectURIs = [ "/device/callback" ];
          }
          {
            id = dashboard.client_id;
            public = false;
            name = dashboard.client_id;
            secret = dashboard.client_secret;
            redirectURIs = [ dashboard.redirect_uri ];
          }
        ];
      };
    };
  };

}
