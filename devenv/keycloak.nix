{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.lomasKeycloak;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  # We need some kind of certificates to start Keycloak in production mode
  certSelfSigned = pkgs.runCommand "selfSignedCerts" { buildInputs = [ pkgs.openssl ]; } ''
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -nodes -subj '/CN=${cfg.kc_hostname}'
    mkdir -p $out
    cp key.pem cert.pem $out
  '';

  dbPassword = "${cfg.homeDir}/db_password";

  # We have to construct the conf file now to build keycloak package since it's doing a wierd pre-build/configure
  confFile = pkgs.writeText "keycloak.conf" ''
    db=postgres
    db-password=${dbPassword}
    db-url-database=keycloak
    db-url-host=${cfg.postgres_addr}
    db-url-port=${toString cfg.postgres_port}
    db-url-properties=
    db-username=keycloak
    hostname=${cfg.kc_hostname}
    hostname-backchannel-dynamic=false
    http-relative-path=/
    https-certificate-file=${cfg.homeDir}/ssl/cert.pem
    https-certificate-key-file=${cfg.homeDir}/ssl/key.pem
    https-port=${toString cfg.kc_https_port}
    http-enabled=true
    http-port=${toString cfg.kc_http_port}
    http-management-port=${toString cfg.kc_management_port}
    https-management-certificate-file=
    https-management-certificate-key-file=
    health-enabled=true
  '';

  # Building/setting up package (kc.sh build steps, required for --optimized run)
  keycloakPkg = pkgs.keycloak.override { inherit confFile; };
in
{

  options.lomasKeycloak = {
    enable = mkEnableOption "Enable lomas Keycloak Service";

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

    kc_http_port = mkOption {
      type = types.int;
      description = "Keycloak http port";
    };

    kc_https_port = mkOption {
      type = types.int;
      description = "Keycloak https port";
    };

    kc_management_port = mkOption {
      type = types.int;
      description = "Keycloak Management port";
    };

    kc_hostname = mkOption {
      type = types.str;
      default = "localhost";
      example = "keycloak.domain";
      description = "Keycloak Hostname";
    };

    kc_bootstrapAdminUser = mkOption {
      type = types.str;
      default = "admin";
      example = "admin";
      description = "Keycloak boostrap Admin Username";
    };

    kc_bootstrapAdminPass = mkOption {
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
      KC_BOOTSTRAP_ADMIN_USERNAME = cfg.kc_bootstrapAdminUser;
      KC_BOOTSTRAP_ADMIN_PASSWORD = cfg.kc_bootstrapAdminPass;
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
        echo ${cfg.kc_bootstrapAdminPass} > ${dbPassword}

        mkdir -p ${cfg.homeDir}/ssl
        cp -u ${certSelfSigned}/{cert,key}.pem ${cfg.homeDir}/ssl/
        ${keycloakPkg}/bin/kc.sh --verbose start --optimized
      '';

      process-compose = {
        depends_on.postgres.condition = "process_healthy";
        readiness_probe = {
          http_get = {
            scheme = "http";
            host = "127.0.0.1";
            port = cfg.kc_management_port;
            path = "/health/ready";
          };
          initial_delay_seconds = 15;
          failure_threshold = 10;
        };
      };
    };

    # Keycloak setup for lomas
    processes.keycloak_setup = {
      exec = "lomas-keycloak-setup";
      process-compose = {
        working_dir = "$DEVENV_ROOT/server/lomas_server";
        depends_on.keycloak.condition = "process_healthy";
      };
    };

    # Keycloak requires a postgres
    services.postgres = {
      enable = true;
      port = cfg.postgres_port;
      listen_addresses = cfg.postgres_addr;
      initialDatabases = [
        {
          name = "keycloak";
          user = "keycloak";
          pass = cfg.kc_bootstrapAdminPass;
        }
      ];
    };

    # cheeky override of postgres statup command to force a clean start
    processes.postgres.process-compose.command = "rm -rvf ${config.env.PGDATA} && ${config.processes.postgres.exec}";

  };
}
