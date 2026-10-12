{ inputs, lib, ... }:
let
  inherit (import ../_lib.nix { inherit lib; }) portStr;
in
{
  options.perSystem = inputs.flake-parts.lib.mkPerSystemOption (
    {
      self',
      config,
      lib,
      pkgs,
      ...
    }:
    {
      imports = [ ../_defaults.nix ];

      options.dev.dashboard = {
        package = lib.mkOption {
          type = lib.types.package;
          default = self'.packages.lomasEnv;
        };

        port = lib.mkOption {
          type = portStr;
          default = config.ports.streamlit;
          description = "Garage port";
        };

        baseUrl = lib.mkOption {
          type = lib.types.str;
          default = "/admin";
          example = "\"\" /admin /dashboard";
          description = "Lomas Dashboard Base Url";
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
      cfg = config.dev.dashboard;
      toml = pkgs.formats.toml { };
      secretFile = toml.generate "secrets.toml" {
        auth = {
          inherit (config.dev.dex.oidc.clients.adminDashboard) client_id client_secret redirect_uri;
          server_metadata_url = config.dev.dex.discoveryUrl;
          cookie_secret = "changeme";
          expose_tokens = [
            "access"
            "id"
          ];
        };
      };

      src = builtins.path {
        name = "lomasAdminDashboard";
        path = ../../server/lomas_server;
      };

      # polars: RuntimeError: could not execute mprotect for CPUID check
      # MemoryDenyWriteExecute=no (?)
      dashboard-unit = pkgs.writeText "dashboard.service" ''
        [Unit]
        Description=Lomas Admin Dashboard

        [Service]
        Type=simple
        ExecStart=${cfg.package}/bin/streamlit run ${src}/administration/dashboard/about.py
        Environment="HOME=/"
        Environment="STREAMLIT_SERVER_PORT=${cfg.port}"
        Environment="STREAMLIT_SERVER_BASE_URL_PATH=${cfg.baseUrl}"
        Environment="STREAMLIT_SECRETS_FILE=${secretFile}"
        Environment="STREAMLIT_SERVER_HEADLESS=true"
        Environment="STREAMLIT_BROWSER_GATHER_USAGE_STATS=0"
      '';
    in
    {
      packages.dashboard-service = pkgs.portableService {
        pname = "dashboard";
        version = "1";
        units = [ dashboard-unit ];
      };
    };
}
