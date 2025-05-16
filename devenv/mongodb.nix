{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomasMongo;

  inherit (lib)
    types
    mkIf
    mkForce
    mkOption
    mkEnableOption
    getExe
    ;
in
{
  options.lomasMongo = {
    enable = mkEnableOption "Enable Lomas MongoDB";

    addr = mkOption {
      type = types.str;
      default = "localhost";
      example = "mongo.domain";
      description = "MongoDB Server address";
    };

    port = mkOption {
      type = types.int;
      default = 27017;
      description = "MongoDB port";
    };

    dbName = mkOption {
      type = types.str;
      default = "defaultdb";
      description = "MongoDB default database name";
    };

    extraDbNames = mkOption {
      type = types.listOf types.str;
      default = [ ];
      example = [ "testdb" ];
      description = "Extra database to create (zb. for testing/integration)";
    };

    initialUser = mkOption {
      type = types.str;
      description = "MongoDB default initialUser name";
    };

    initialPassword = mkOption {
      type = types.str;
      description = "MongoDB default initialPassword name";
    };

    user = mkOption {
      type = types.str;
      description = "MongoDB default user name";
    };

    password = mkOption {
      type = types.str;
      description = "MongoDB default user password";
    };

    dsn = mkOption {
      readOnly = true;
      type = types.str;
      default = "mongodb://${cfg.addr}:${toString cfg.port}/${cfg.dbName}";
      description = "MongoDB url/dsn format";
    };
  };

  config = mkIf cfg.enable {
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
            ${getExe pkgs.mongosh} --port ${toString cfg.port} ${dbName} >/dev/null <<-EOJS
                db.createUser({
                  user: "${user}",
                  pwd: "${pwd}",
                  roles: [{role: "readWrite", db: "${dbName}" }]
                });
            EOJS
          '';
        configureScript = pkgs.writeShellScriptBin "configure-mongodb" (
          lib.strings.concatLines (
            [
              "set -euo pipefail"
              # Initial admin database
              (createUserDB {
                dbName = "admin";
                user = cfg.initialUser;
                pwd = cfg.initialPassword;
              })
              # Initial user database
              (createUserDB { dbName = cfg.dbName; })
            ]
            # Extra databases
            ++ (map (extraDb: createUserDB { dbName = extraDb; }) cfg.extraDbNames)
          )
        );
      in
      {
        process-compose.depends_on.mongodb.condition = "process_healthy";
        # override mongodb-configure original script
        exec = mkForce "${configureScript}/bin/configure-mongodb";
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
