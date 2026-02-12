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

  inherit (config.lomas.oidc.clients)
    apiServer
    apiClient
    adminDashboard
    grafanaDashboard
    ;

  # Write config as file
  confFile = pkgs.writeText "dex-config.yaml" (''
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

    expiry:
      deviceRequests: "5m"
      signingKeys: "6h"
      idTokens: "1m"
      refreshTokens:
        disableRotation: false
        reuseInterval: "3s"
        validIfNotUsedFor: "1m" # "2160h" # 90 days
        absoluteLifetime: "3960h" # 165 days

    staticClients:
      # lomas api server
      - id: ${apiServer.client_id}
        public: false
        name: ${apiServer.client_id}
        secret: ${apiServer.client_secret}
      # lomas client lib
      - id: ${apiClient}
        public: true
        name: ${apiClient}
        redirectURIs:
          # Enables device auth flow
          - '/device/callback'
      # lomas dashboard
      - id: ${adminDashboard.client_id}
        public: false
        name: ${adminDashboard.client_id}
        secret: ${adminDashboard.client_secret}
        redirectURIs:
          - http://${config.lomas.dashboard.host}:${toString config.lomas.dashboard.port}/oauth2callback
      # lomas grafana
      - id: ${grafanaDashboard.client_id}
        public: false
        name: ${grafanaDashboard.client_id}
        secret: ${grafanaDashboard.client_secret}
        redirectURIs:
          - http://${config.lomas.telemetry.services.grafana.host}:${toString config.lomas.telemetry.services.grafana.port}/login/generic_oauth

    staticPasswords:
      # Beware: static passwords cannot be deleted in dex.
  '');

  apiProtoDrv =
    protoPath:
    pkgs.stdenv.mkDerivation rec {
      pname = "dex-api-proto";
      version = "v${cfg.package.version}";

      src = pkgs.fetchurl {
        url = "https://raw.githubusercontent.com/dexidp/dex/${version}/api/v2/api.proto";
        hash = "sha256-nYdmSeTbgl7wD/Rl3xSoL2l+mOt2tGXOkmO5iJepLgo=";
      };

      buildInputs = [ pkgs.python3Packages.grpcio-tools ];

      dontUnpack = true;
      dontConfigure = true;

      buildPhase = ''
        install -Dm644 $src "$out/${protoPath}/api.proto"
        cd $out
        python-grpc-tools-protoc -I. --pyi_out=. --python_out=. --grpc_python_out=. "${protoPath}/api.proto"
        rm ${protoPath}/api.proto
      '';
    };
in
{
  # Define Dex config options
  options.lomas.dex = {
    enable = mkEnableOption "Enable Dex";

    package = mkOption {
      type = types.package;
      # default = pkgs.dex-oidc;
      default = pkgs.dex-oidc.overrideAttrs (old: rec{
        version = "c016300db963097d7a90eb010ae2f323dd54b0b7";
        src = pkgs.fetchFromGitHub {
          owner = "dexidp";
          repo = "dex";
          rev = "${version}";
          sha256="sha256-COUhIxskcfnTF/TRmfb3IQ6Do+xdRV4xeNUspytc1Xw=";
        };
        patches = [
          (pkgs.fetchpatch{
            url = "https://github.com/dexidp/dex/commit/cccbebc146f95ddad890fd2307c9c0bf5497ecee.patch";
            sha256 = "sha256-NsnqN+VeXi3NZ2zsp9KE5/9zqX9CioRrr0N313ZG3G0=";
          })
        ];
        vendorHash="sha256-obnZ8DOCDSK2cqu6PNjAeQbkb24osRGwM6fq93WZpOc=";
        passthru.tests = {
          version = pkgs.testers.testVersion {
            version = "${version}";
          };
        };
      });
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

    protoPath = mkOption {
      type = types.str;
      default = "lomas_server/administration/dex/api";
      description = ''
        Path to generate protobuf api
        Does influence the import name in python
      '';
    };

  };

  config = mkIf cfg.enable {
    packages = [ cfg.package ];
    processes.dex = {
      exec = "${lib.getExe cfg.package} serve ${confFile}";
      process-compose = {
        readiness_probe.http_get = {
          scheme = "http";
          inherit (cfg) host port;
          path = "/dex";
        };
      };
    };

    tasks."filegen:dex-api-proto" = {
      before = [ "devenv:enterShell" ];
      exec = "cp -u -r ${apiProtoDrv cfg.protoPath}/lomas_server ./server";
    };

    # can be provided with password [SALT] for reproducible outputs
    scripts.hash-dex-password.exec = ''
      ${lib.getExe pkgs.mkpasswd} -m bcrypt -R 12 "$@"
    '';

  };
}
