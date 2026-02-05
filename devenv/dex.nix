{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.dex;
  lomas_cfg = config.lomas;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  inherit (import ./utils.nix lib) wrapScript;
  inherit (import ./utils.nix lib) clientIdSecret;

  # Write config as file
  confFile = pkgs.writeText "dex-conf.yaml" (''
    issuer: http://${cfg.host}:${toString cfg.port}/dex
    web:
      http: ${cfg.address}:${toString cfg.port}

    storage:
      type: sqlite3
      config:
        file: $XDG_RUNTIME_DIR/dex.db

    grpc:
      addr: ${cfg.adminAddress}:${toString cfg.adminPort}

    # Enable local users
    enablePasswordDB: true
    # Allow password grants with local users
    oauth2:
      passwordConnector: local

    staticClients:
      # lomas api server
      - id: ${config.lomas.oidc.clients.apiServer.client_id}
        public: false
        name: ${config.lomas.oidc.clients.apiServer.client_id}
        secret: ${config.lomas.oidc.clients.apiServer.client_secret}
      # lomas client lib
      - id: ${config.lomas.oidc.clients.apiClient}
        public: true
        name: ${config.lomas.oidc.clients.apiClient}
        redirectURIs:
          # Enables device auth flow
          - '/device/callback'
      # lomas dashboard
      - id: ${config.lomas.oidc.clients.adminDashboard.client_id}
        public: false
        name: ${config.lomas.oidc.clients.adminDashboard.client_id}
        secret: ${config.lomas.oidc.clients.adminDashboard.client_secret}
        redirectURIs:
          - http://${config.lomas.dashboard.host}:${toString config.lomas.dashboard.port}/oauth2callback
      # lomas grafana
      - id: ${config.lomas.oidc.clients.grafanaDashboard.client_id}
        public: false
        name: ${config.lomas.oidc.clients.grafanaDashboard.client_id}
        secret: ${config.lomas.oidc.clients.grafanaDashboard.client_secret}
        redirectURIs:
          - http://${config.lomas.telemetry.services.grafana.host}:${toString config.lomas.telemetry.services.grafana.port}/login/generic_oauth

    staticPasswords:
      # Beware: static passwords cannot be deleted in dex.
  '');
in
{
  # Define Dex config options
  options.lomas.dex = {
    enable = mkEnableOption "Enable Dex";

    package = mkOption {
      type = types.package;
      default = pkgs.dex-oidc;
      # Trying out nightly, does not work yet
      # default = pkgs.dex-oidc.overrideAttrs (old: {
      #   version = "master";
      #   src = pkgs.fetchFromGitHub {
      #     owner = "dexidp";
      #     repo = "dex";
      #     rev = "${old.version}";
      #     sha256=lib.fakeHash;
      #   };
      #   passthru.tests = {
      #     version = pkgs.testers.testVersion {
      #       version = "${old.version}";
      #     };
      #   };
      # });
    };

    port = mkOption {
      type = types.port;
      description = "Dex http port";
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

    adminPort = mkOption {
      type = types.port;
      description = "Dex admin http port";
    };

    adminAddress = mkOption {
      type = types.str;
      default = cfg.address;
      description = "Dex admin bind address";
    };

  };

  config = mkIf cfg.enable {
    packages = [ cfg.package ];
    processes.dex = {
      exec = "${lib.getExe cfg.package} serve ${confFile}";
      process-compose = {
        is_tty = true;
        readiness_probe.http_get = {
          scheme = "http";
          inherit (cfg) host port;
          path = "/dex";
        };
      };
    };

    scripts.gen-dex-api =
      let
        proto_dir = "./lomas_server/administration/dex/api";
        proto_path = "${proto_dir}/api.proto";
      in
      wrapScript {
        exec = ''
          pushd server
          mkdir -p ${proto_dir}

          wget -O ${proto_path} https://raw.githubusercontent.com/dexidp/dex/v${cfg.package.version}/api/v2/api.proto
          python -m grpc_tools.protoc -I. --pyi_out=. --python_out=. --grpc_python_out=. ${proto_path}

          rm ${proto_path}
          popd
        '';
      };

    scripts.hash-dex-password.exec = ''
      python ${pkgs.writeText "hash_pwd.py" ''
        import sys
        import bcrypt

        def hash_pwd(password: str) -> bytes:
            bytes_ = password.encode("utf-8")
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(bytes_, salt)

        if len(sys.argv) != 2:
            print("usage: hash-password <password>", file=sys.stderr)
            sys.exit(1)

        password = sys.argv[1]
        print(hash_pwd(password).decode("utf-8"))
      ''} "$@"
    '';
  };
}
