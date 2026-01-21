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

  inherit (import ./utils.nix lib) wrapScript;

  clientIdSecret = types.submodule {
    options.client_id = mkOption {
      type = types.str;
    };
    options.client_secret = mkOption {
      type = types.str;
    };
    options.redirect_uri = mkOption {
      default = null;
      type = types.nullOr types.str;
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
      default = "/";
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

    oidc.enable = mkEnableOption "Enable OIDC for lomas";

    oidc.providerUrl = mkOption {
      type = types.str;
      description = "OIDC provider url.";
    };

    oidc.discoveryUrl = mkOption {
      type = types.str;
      default = "${cfg.oidc.providerUrl}/.well-known/openid-configuration";
      description = "OIDC provider discovery url.";
    };

    # TODO better name for this?
    oidc.queryUserinfo = mkOption {
      type = types.bool;
      description = "Whether to query the userinfo endpoint or parse access tokens as jwts.";
    };

    oidc.clients.apiServer = mkOption {
      type = clientIdSecret;
      description = "OIDC client for api server";
    };

    oidc.clients.apiClient = mkOption {
      type = types.str;
      description = "OICD public client name for api client";
    };

    oidc.clients.adminDashboard = mkOption {
      type = clientIdSecret;
      description = "OIDC client for admin dashboard";
    };

    oidc.clients.grafanaDashboard = mkOption {
      type = clientIdSecret;
      description = "OIDC client for grafana dashboard";
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
        working_dir = "${config.env.DEVENV_ROOT}/server/lomas_server";
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
        working_dir = "${config.env.DEVENV_ROOT}/server/lomas_server";
        depends_on.rabbitmq.condition = "process_healthy";
        replicas = 2;
        # Un-comment to observe worker logs.
        # log_location = "$DEVENV_ROOT/logs/worker.log";
      };
    };

    processes.admin-dashboad =
      let
        inherit (cfg.oidc.clients.adminDashboard) client_id client_secret redirect_uri;
        secretFile = pkgs.writeText "secrets.toml" ''
          [auth]
          client_id = "${client_id}"
          client_secret = "${client_secret}"
          redirect_uri = "${redirect_uri}"
          server_metadata_url = "${cfg.oidc.discoveryUrl}"
          cookie_secret = "changeme"
          expose_tokens = [ "access", "id" ]
        '';
      in
      {
        exec = ''
          streamlit run \
            --server.headless true \
            --server.baseUrlPath=${cfg.dashboard.baseUrl} \
            --secrets.files=${secretFile} \
            lomas_server/administration/dashboard/about.py
        '';
        process-compose = {
          working_dir = "${config.env.DEVENV_ROOT}/server";
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

    scripts.run-jupyter =
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
      wrapScript {
        pwd = "client";
        exec = "jupyter notebook ${builtins.concatStringsSep " " args}";
      };

  };
}
