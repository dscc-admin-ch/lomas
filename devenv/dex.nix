{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.dex;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  # Write config as file
  confFile = pkgs.writeText "dex-conf.yaml" (''
    issuer: http://${cfg.host}:${toString cfg.port}/dex
    web:
      http: ${cfg.address}}:${toString cfg.port} # TODO set interface?
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

    # staticClients:
    #   - id: public-client
    #     public: true
    #     name: 'Public Client'
    #     redirectURIs:
    #       - 'http://127.0.0.1/callback'
    #   - id: device-client
    #     public: true
    #     name: 'Device Client'
    #     redirectURIs:
    #       - '/device/callback'
  '');
in
{
  # Define Dex config options
  options.lomas.dex = {
    enable = mkEnableOption "Enable Dex";

    package = mkOption {
      type = types.package;
      default = pkgs.dex-oidc;
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
      default = "127.0.0.1";
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
  };
}
