{
  pkgs,
  lib,
  config,
  ...
}:

let
  inherit (lib) types;
  cfg = config.lomasMongo;
in
{
  options.lomasMongo = {
    enable = lib.mkEnableOption "Enable Lomas MongoDB";

    addr = lib.mkOption {
      type = types.str;
      default = "localhost";
      example = "mongo.domain";
      description = "MongoDB Server address";
    };

    port = lib.mkOption {
      type = types.int;
      default = 27017;
      description = "MongoDB port";
    };

    dbName = lib.mkOption {
      type = types.str;
      default = "defaultdb";
      description = "MongoDB default database name";
    };

    initialUser = lib.mkOption {
      type = types.str;
      description = "MongoDB default initialUser name";
    };

    initialPassword = lib.mkOption {
      type = types.str;
      description = "MongoDB default initialPassword name";
    };

    user = lib.mkOption {
      type = types.str;
      description = "MongoDB default user name";
    };

    password = lib.mkOption {
      type = types.str;
      description = "MongoDB default user password";
    };

    dsn = lib.mkOption {
      readOnly = true;
      type = types.str;
      default = "mongodb://${cfg.addr}:${toString cfg.port}/${cfg.dbName}";
      description = "MongoDB url/dsn format";
    };
  };

  config = lib.mkIf cfg.enable {
    packages = [ pkgs.mongosh ];

    services.mongodb = {
      enable = true;
      additionalArgs = [
        "--port"
        (toString cfg.port)
      ];
      initDatabaseUsername = cfg.initialUser;
      initDatabasePassword = cfg.initialPassword;
    };

    processes.mongodb-configure =
      let
        createUserDB =
          {
            dbName,
            user ? cfg.user,
            pwd ? cfg.password,
          }:
          ''
            echo "Creating user/database: ${user}/${dbName}"
            ${lib.getExe pkgs.mongosh} --port ${toString cfg.port} ${dbName} >/dev/null <<-EOJS
                db.createUser({
                  user: "${user}",
                  pwd: "${pwd}",
                  roles: [{role: "readWrite", db: "${dbName}" }]
                });
            EOJS
          '';
        configureScript = pkgs.writeShellScriptBin "configure-mongodb" (
          lib.strings.concatLines [
            "set -euo pipefail"
            (createUserDB {
              dbName = "admin";
              user = cfg.initialUser;
              pwd = cfg.initialPassword;
            })
            (createUserDB { dbName = cfg.dbName; })
            (createUserDB { dbName = "testdb"; })
          ]
        );
      in
      {
        process-compose.depends_on.mongodb.condition = "process_healthy";
        # override mongodb-configure original script
        exec = lib.mkForce "${configureScript}/bin/configure-mongodb";
      };

    processes.mongodb.process-compose = {
      readiness_probe = {
        exec.command = "${lib.getExe pkgs.mongosh} --quiet --eval '{ ping: 1 }' --port ${toString cfg.port} &>/dev/null";
        initial_delay_seconds = 10;
        period_seconds = 3;
        timeout_seconds = 3;
        success_threshold = 2;
        failure_threshold = 10;
      };
    };

  };
}
