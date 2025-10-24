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

    baseUrl = mkOption {
      type = types.str;
      example = "/api, /api/v1, /";
      description = "Lomas Api base Url";
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

    dashboard.baseUrl = mkOption {
      type = types.str;
      default = "/admin";
      example = "\"\" /admin /dashboard";
      description = "Lomas Dashboard Base Url";
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

    client.jupyter.port = mkOption {
      type = types.int;
      description = "Lomas Client's Jupyter port";
    };

    client.jupyter.password = mkOption {
      type = types.nullOr types.str;
      description = "Lomas Client's Jupyter password";
    };

  };

  config = mkIf cfg.enable {
    processes.lomas-server = {
      exec = "python uvicorn_serve.py";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server/lomas_server";
        depends_on.mongodb.condition = "process_healthy";
        readiness_probe.failure_threshold = if (config.env.LOMAS_SERVICE_server__reload == "true") then 100 else 3;
        readiness_probe.http_get = {
          scheme = "http";
          host = cfg.host;
          port = cfg.port;
          path = "/live";
        };
      };
    };

    ##########
    # WORKER #
    ##########

    processes.worker = {
      # helpful to investigate/debug watchexec: --print-events
      exec = "${lib.getExe pkgs.watchexec} --watch=$DEVENV_ROOT -e py --restart --no-meta python worker.py";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server/lomas_server";
        depends_on.rabbitmq.condition = "process_healthy";
        replicas = 2;
        # Un-comment to observe worker logs.
        # log_location = "$DEVENV_ROOT/logs/worker.log";
      };
    };

    processes.admin-dashboad = {
      exec = "streamlit run --server.headless true --server.baseUrlPath=${cfg.dashboard.baseUrl} lomas_server/administration/dashboard/about.py";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server";
        environment = [
          "STREAMLIT_SERVER_PORT=${toString cfg.dashboard.port}"
          "STREAMLIT_BROWSER_GATHER_USAGE_STATS=0"
        ];
        readiness_probe.http_get = {
          host = cfg.dashboard.host;
          port = cfg.dashboard.port;
          path = "${cfg.dashboard.baseUrl}/ping";
        };
      };
    };

    scripts.run-jupyter.exec =
      let
        # Build argon2 hashed password with jupyter static parameters
        hashed_password_drv = pkgs.runCommand "jupyterHashedPassword" { } ''
          echo -n ${cfg.client.jupyter.password} | ${pkgs.libargon2}/bin/argon2 lomasSalt -id -k 10240 -t 10 -p 8 -e > $out
        '';
        # jupyter format add a prefix to argon2 standard hash format
        hashed_password = "argon2:${lib.trim (builtins.readFile hashed_password_drv)}";

        args = [
          "--ServerApp.ip=0.0.0.0"
          "--ServerApp.port=${toString cfg.client.jupyter.port}"
          "--ServerApp.allow_root=True"
          "--ServerApp.open_browser=False"
          "--ExtensionApp.open_browser=False"
          "--IdentityProvider.token=''"
          (lib.optionalString (
            cfg.client.jupyter.password != null
          ) "--PasswordIdentityProvider.hashed_password='${hashed_password}'")
        ];
      in
      ''
        pushd $DEVENV_ROOT/client
        jupyter notebook ${builtins.concatStringsSep " " args}
        popd > /dev/null
      '';

  };
}
