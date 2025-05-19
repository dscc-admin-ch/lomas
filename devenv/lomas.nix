{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  clientIdSecret = types.submodule {
    options.client_id = mkOption {
      type = types.str;
    };
    options.client_secret = mkOption {
      type = types.str;
    };
  };
in
{
  options.lomas = {
    enable = mkEnableOption "Enable Lomas Itself";

    host = mkOption {
      type = types.str;
      default = "localhost";
      example = "lomas-server.domain";
      description = "Lomas Server address";
    };

    port = mkOption {
      type = types.int;
      description = "Lomas Server port";
    };

    dashboard.host = mkOption {
      type = types.str;
      default = "localhost";
      example = "lomas-dashboard.domain";
      description = "Lomas Dashboard address";
    };

    dashboard.port = mkOption {
      type = types.int;
      description = "Lomas Dashboard port";
    };

    realm = mkOption {
      type = types.str;
      default = "lomas";
      description = "Lomas Server Authentication Realm";
    };

    admin = mkOption {
      type = clientIdSecret;
    };

    api = mkOption {
      type = clientIdSecret;
    };

  };

  config = mkIf cfg.enable {
    processes.lomas-server = {
      exec = "python uvicorn_serve.py";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server/lomas_server";
        depends_on.mongodb.condition = "process_healthy";
        readiness_probe.http_get = {
          scheme = "http";
          host = cfg.host;
          port = cfg.port;
          path = "/live";
        };
      };
    };

    processes.admin-dashboad = {
      exec = "streamlit run --server.headless true lomas_server/administration/dashboard/about.py";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server";
        environment = [
          "STREAMLIT_SERVER_PORT=${toString cfg.dashboard.port}"
          "STREAMLIT_BROWSER_GATHER_USAGE_STATS=0"
        ];
        readiness_probe.http_get = {
          host = cfg.dashboard.host;
          port = cfg.dashboard.port;
          path = "/ping";
        };
      };
    };

  };
}
