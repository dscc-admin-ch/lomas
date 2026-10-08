{ inputs, lib, ... }:
let
  inherit (import ../_lib.nix { inherit lib; }) portStr clientIdSecret;
in
{
  options.perSystem = inputs.flake-parts.lib.mkPerSystemOption (
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      inherit (lib)
        types
        mkOption
        ;
      cfg = config.dev.dex;
    in
    {
      options.dev.dex = {
        package = mkOption {
          type = types.package;
          default = pkgs.dex-oidc.overrideAttrs (_old: rec {
            version = "2.44.0";
            src = pkgs.fetchFromGitHub {
              owner = "dexidp";
              repo = "dex";
              rev = "v${version}";
              sha256 = "sha256-wpy7pZBpqAaPjWbnsqtnE+65a58IGg0pyp4CEUnmmc4=";
            };
            patches = [
              (pkgs.fetchpatch {
                url = "https://github.com/dexidp/dex/commit/cccbebc146f95ddad890fd2307c9c0bf5497ecee.patch";
                sha256 = "sha256-NsnqN+VeXi3NZ2zsp9KE5/9zqX9CioRrr0N313ZG3G0=";
              })
            ];
            vendorHash = "sha256-3ef2G4+UlLGsBW09ZM20qU82uj/hVlMAnujcd2BulGg=";
          });
        };

        host = mkOption {
          type = types.str;
          default = "localhost";
          example = "dex.domain";
          description = "Dex hostname";
        };

        address = mkOption {
          type = types.str;
          default = "127.0.0.1";
          description = "Dex bind address";
        };

        apiPort = mkOption {
          type = portStr;
          default = 4445;
          description = "Dex API port";
        };

        grpcPort = mkOption {
          type = portStr;
          default = 4446;
          description = "Dex gRPC port";
        };

        path = mkOption {
          type = types.str;
          default = "/dex";
          example = "/ /dex";
          description = "Dex Base Url";
        };

        adminAddress = mkOption {
          type = types.str;
          default = cfg.address;
          description = "Dex admin bind address";
        };

        protoPath = mkOption {
          type = types.str;
          default = "lomas_server/administration/dex/api";
          description = ''
            Path to generate protobuf api
            Does influence the import name in python
          '';
        };

        providerUrl = mkOption {
          type = types.str;
          internal = true;
          default = "http://${cfg.host}:${cfg.apiPort}${cfg.path}";
          description = "OIDC provider url.";
        };

        discoveryUrl = mkOption {
          type = types.str;
          internal = true;
          default = "${cfg.providerUrl}/.well-known/openid-configuration";
          description = "OIDC provider discovery url.";
        };

        grpcUrl = mkOption {
          type = types.str;
          internal = true;
          default = "${cfg.adminAddress}:${cfg.grpcPort}";
          description = "gRPC admin Url";
        };

        oidc.clients = {
          apiServer = mkOption {
            type = clientIdSecret;
            description = "OIDC client for api server";
          };
          apiClient = mkOption {
            type = types.str;
            description = "OICD public client name for api client";
          };
          adminDashboard = mkOption {
            type = clientIdSecret;
            description = "OIDC client for admin dashboard";
          };
          grafanaDashboard = mkOption {
            type = clientIdSecret;
            description = "OIDC client for grafana dashboard";
          };
        };

      };
    }
  );

  config.perSystem =
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      cfg = config.dev.dex;
      cfgOidc = cfg.oidc.clients;
    in
    {
      packages.dex-service =
        let
          dexConfig = pkgs.writeText "dex-config.yaml" ''
            issuer: ${cfg.providerUrl}
            web:
              http: ${cfg.host}:${cfg.apiPort}
            storage:
              type: memory
            grpc:
              addr: ${cfg.grpcUrl}
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
              - id: ${cfgOidc.apiServer.client_id}
                public: false
                name: ${cfgOidc.apiServer.client_id}
                secret: ${cfgOidc.apiServer.client_secret}
              # lomas client lib
              - id: ${cfgOidc.apiClient}
                public: true
                name: ${cfgOidc.apiClient}
                redirectURIs:
                  # Enables device auth flow
                  - "/device/callback"
              # lomas dashboard
              - id: ${cfgOidc.adminDashboard.client_id}
                public: false
                name: ${cfgOidc.adminDashboard.client_id}
                secret: ${cfgOidc.adminDashboard.client_secret}
                redirectURIs:
                  - ${cfgOidc.adminDashboard.redirect_uri}
              # lomas grafana
              - id: ${cfgOidc.grafanaDashboard.client_id}
                public: false
                name: ${cfgOidc.grafanaDashboard.client_id}
                secret: ${cfgOidc.grafanaDashboard.client_secret}
                redirectURIs:
                  - ${cfgOidc.grafanaDashboard.redirect_uri}
            # Beware: static passwords cannot be deleted in dex.
            staticPasswords:
          '';

          dex-unit = pkgs.writeText "dex.service" ''
            [Unit]
            Description=Identity service OpenID Connect
            Documentation=https://dexidp.io/docs/

            [Service]
            Type=simple
            ExecStart=${lib.getExe cfg.package} serve ${dexConfig}
            TimeoutStopSec=2
          '';
        in
        pkgs.portableService {
          pname = "dex";
          version = "1";
          units = [ dex-unit ];
        };
    };

}
