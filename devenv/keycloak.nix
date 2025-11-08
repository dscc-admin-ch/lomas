{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.lomas.keycloak;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  # We need some kind of certificates to start Keycloak in production mode
  certSelfSigned = pkgs.runCommand "selfSignedCerts" { buildInputs = [ pkgs.openssl ]; } ''
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -nodes -subj '/CN=${cfg.host}'
    mkdir -p $out
    cp key.pem cert.pem $out
  '';

  enablePostgres = cfg.db == "postgres";

  dbPassword = "${cfg.homeDir}/db_password";

  # We have to construct the conf file now to build keycloak package since it's doing a wierd pre-build/configure
  confFile = pkgs.writeText "keycloak.conf" (
    lib.concatLines [
      ''
        db=${cfg.db}
        hostname=${cfg.host}
        hostname-backchannel-dynamic=false
        http-relative-path=/
        https-certificate-file=${cfg.homeDir}/ssl/cert.pem
        https-certificate-key-file=${cfg.homeDir}/ssl/key.pem
        https-port=${toString cfg.httpsPort}
        http-enabled=true
        http-port=${toString cfg.httpPort}
        http-management-port=${toString cfg.httpManagementPort}
        https-management-certificate-file=
        https-management-certificate-key-file=
        health-enabled=true
      ''
      (lib.optionalString enablePostgres ''
        db-password=${dbPassword}
        db-url-database=keycloak
        db-url-host=${cfg.postgres_addr}
        db-url-port=${toString cfg.postgres_port}
        db-url-properties=
        db-username=keycloak
      '')
    ]
  );

  # Building/setting up package (kc.sh build steps, required for --optimized run)
  keycloakPkg = pkgs.keycloak.override { inherit confFile; };
in
{

  options.lomas.keycloak = {
    enable = mkEnableOption "Enable lomas Keycloak Service";

    db = mkOption {
      type = types.enum [
        "dev-mem"
        "postgres"
      ];
      description = "Backend database type.";
      default = "dev-mem";
    };

    postgres_port = mkOption {
      type = types.int;
      default = 5432;
      description = "PostgreSQL port";
    };

    postgres_addr = mkOption {
      type = types.str;
      default = "localhost";
      example = "postgres.domain";
      description = "PostgreSQL address";
    };

    httpPort = mkOption {
      type = types.int;
      description = "Keycloak http port";
    };

    httpsPort = mkOption {
      type = types.int;
      description = "Keycloak https port";
    };

    httpManagementPort = mkOption {
      type = types.int;
      description = "Keycloak Management port";
    };

    host = mkOption {
      type = types.str;
      default = "localhost";
      example = "keycloak.domain";
      description = "Keycloak Hostname";
    };

    bootstrapAdminUser = mkOption {
      type = types.str;
      default = "admin";
      example = "admin";
      description = "Keycloak boostrap Admin Username";
    };

    bootstrapAdminPass = mkOption {
      type = types.str;
      description = "Keycloak boostrap Admin Password";
    };

    homeDir = mkOption {
      type = types.str;
      default = "${config.devenv.state}/keycloak";
      description = "Keycloak Home directory";
    };

    confDir = mkOption {
      type = types.str;
      default = "${config.devenv.state}/conf";
      description = "Keycloak Config directory";
    };
  };

  config = mkIf cfg.enable {
    env = {
      # Theses are critical and used by kc.sh at startup !
      KC_HOME_DIR = cfg.homeDir;
      KC_CONF_DIR = cfg.confDir;
      # Theses are used by lomas-keycloak-setup
      KC_BOOTSTRAP_ADMIN_USERNAME = cfg.bootstrapAdminUser;
      KC_BOOTSTRAP_ADMIN_PASSWORD = cfg.bootstrapAdminPass;
    };

    packages = [ pkgs.openssl ];

    processes.keycloak = {
      exec = ''
        set -o errexit -o pipefail -o nounset -o errtrace
        shopt -s inherit_errexit
        umask u=rwx,g=,o=

        mkdir -p ${cfg.homeDir}/themes
        ln -fs ${keycloakPkg}/providers ${cfg.homeDir}/
        ln -fs ${keycloakPkg}/lib ${cfg.homeDir}/

        install -D -m 0600 ${confFile} ${cfg.homeDir}/conf/keycloak.conf
        echo ${cfg.bootstrapAdminPass} > ${dbPassword}

        mkdir -p ${cfg.homeDir}/ssl
        cp -u ${certSelfSigned}/{cert,key}.pem ${cfg.homeDir}/ssl/
        ${keycloakPkg}/bin/kc.sh start --optimized
      '';

      process-compose = {
        depends_on.postgres = lib.mkIf enablePostgres { condition = "process_healthy"; };
        readiness_probe = {
          http_get = {
            scheme = "http";
            host = "127.0.0.1";
            port = cfg.httpManagementPort;
            path = "/health/ready";
          };
          initial_delay_seconds = 20;
          failure_threshold = 20;
        };
      };
    };

    # Keycloak setup for lomas
    processes.keycloak-setup = {
      exec = "lomas-keycloak-setup";
      process-compose = {
        is_tty = true;
        working_dir = "${config.env.DEVENV_ROOT}/server/lomas_server";
        depends_on.keycloak.condition = "process_healthy";
      };
    };

    # Keycloak requires a postgres
    services.postgres = {
      enable = enablePostgres;
      port = cfg.postgres_port;
      listen_addresses = cfg.postgres_addr;
      initialDatabases = [
        {
          name = "keycloak";
          user = "keycloak";
          pass = cfg.bootstrapAdminPass;
        }
      ];
    };

    tasks = lib.mkIf enablePostgres {
      "devenv:postgres:clean-start" = {
        exec = "rm -rf ${config.env.PGDATA}";
        before = [ "devenv:processes:postgres" ];
      };
    };

  };
}
