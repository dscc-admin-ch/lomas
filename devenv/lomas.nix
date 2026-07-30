{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas;

  inherit (builtins) genList;

  inherit (lib)
    types
    mkIf
    mkMerge
    mkOption
    mkEnableOption
    genAttrs
    ;

  inherit
    (import ./utils.nix {
      inherit lib;
      inherit (config.git) root;
    })
    wrapScript
    ;

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

    baseUrl = mkOption {
      type = types.str;
      default = "/";
      example = "/api, /api/v1, /";
      description = "Lomas Api base Url";
    };

    worker.replicas = mkOption {
      type = types.ints.positive;
      default = 2;
      description = "Number of Worker processes";
    };

    dashboard.host = mkOption {
      type = types.str;
      default = "localhost";
      example = "lomas-dashboard.domain";
      description = "Lomas Dashboard address";
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

    client.jupyter.password = mkOption {
      type = types.nullOr types.str;
      description = "Lomas Client's Jupyter password";
    };

  };

  config = mkIf cfg.enable (mkMerge [
    {
      ##########
      # WORKER #
      ##########
      processes =
        let
          procNames = genList (i: "worker-${toString i}") cfg.worker.replicas;
        in
        genAttrs procNames (name: {
          exec = "exec lomas work";
          cwd = "${config.git.root}/server/lomas_server";
          ready.notify = true;
          watch = {
            paths = [ config.git.root ];
            extensions = [ "py" ];
          };
          after = [
            "devenv:processes:rabbitmq"
          ];
        });
    }

    {
      processes.lomas-server = {
        exec = "exec python cli.py start";
        cwd = "${config.git.root}/server/lomas_server";
        ready = {
          notify = true;
          http.get = {
            inherit (cfg) host;
            port = lib.toInt config.ports.lomas.apiService;
            path = "/live";
          };
          failure_threshold = if (config.env.LOMAS_SERVICE_server__reload == "true") then 100 else 3;
        };
      };

      #############
      # DASHBOARD #
      #############

      env = {
        STREAMLIT_SERVER_PORT = config.ports.streamlit;
        STREAMLIT_SERVER_BASE_URL_PATH = cfg.dashboard.baseUrl;
        STREAMLIT_SERVER_HEADLESS = true;
        STREAMLIT_BROWSER_GATHER_USAGE_STATS = 0;
      };

      processes.admin-dashboard =
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
            exec streamlit run lomas_server/administration/dashboard/about.py
          '';
          cwd = "${config.git.root}/server";
          env = builtins.mapAttrs (name: toString) {
            STREAMLIT_SECRETS_FILES = secretFile;
          };
          ready.http.get = {
            inherit (cfg.dashboard) host;
            port = lib.toInt config.ports.streamlit;
            path = "${cfg.dashboard.baseUrl}/ping";
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
            "--ServerApp.port=${config.ports.jupyter}"
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
    }
  ]);
}
