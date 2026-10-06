{ pkgs, lib, ... }: {
  dex-service =
    let
      dexConfig = pkgs.writeText "dex-config.yaml" ''
        issuer: http://localhost:4445/dex
        web:
          http: 127.0.0.1:4445
        storage:
          type: memory
        grpc:
          addr: 127.0.0.1:4446
        enablePasswordDB: true
        oauth2:
          passwordConnector: local
        expiry:
          deviceRequests: "5m"
          signingKeys: "6h"
          idTokens: "3s"         # Set very short for testing
          refreshTokens:
            disableRotation: false
            reuseInterval: "3s"
            validIfNotUsedFor: "24h" # "2160h" # 90 days
            absoluteLifetime: "3960h" # 165 days
        staticClients:
          # lomas api server
          - id: lomas_api
            public: false
            name: lomas_api
            secret: lomas_api
          # lomas client lib
          - id: lomas_client
            public: true
            name: lomas_client
            redirectURIs:
              # Enables device auth flow
              - "/device/callback"
          # lomas dashboard
          - id: lomas_dashboard
            public: false
            name: lomas_dashboard
            secret: lomas_dashboard
            redirectURIs:
              - http://localhost:8501/admin/oauth2callback
          # lomas grafana
          - id: lomas_grafana
            public: false
            name: lomas_grafana
            secret: lomas_grafana
            redirectURIs:
              - http://localhost:3000/login/generic_oauth
        # Beware: static passwords cannot be deleted in dex.
        staticPasswords:
      '';

      dex-unit = pkgs.writeText "dex.service" ''
        [Unit]
        Description=Identity service OpenID Connect
        Documentation=https://dexidp.io/docs/

        [Service]
        Type=simple
        ExecStart=${lib.getExe pkgs.dex-oidc} serve ${dexConfig}
        TimeoutStopSec=2
      '';
    in
    pkgs.portableService {
      pname = "dex";
      version = "1";
      units = [ dex-unit ];
    };

}
