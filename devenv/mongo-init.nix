{
  pkgs,
  lib,
  mongo_db_name,
  mongo_port,
  initDatabaseUsername,
  initDatabasePassword,
  ...
}:
{
  process-compose.depends_on.mongodb.condition = "process_healthy";
  exec =
    let
      configureScript = pkgs.writeShellScriptBin "configure-mongodb" ''
        set -euo pipefail
        echo "Creating initial user"
        rootAuthDatabase="admin"
        ${pkgs.mongosh}/bin/mongosh --port ${toString mongo_port} "$rootAuthDatabase" >/dev/null <<-EOJS
            db.createUser({
                user: "${initDatabaseUsername}",
                pwd: "${initDatabasePassword}",``
                roles: [ { role: 'root', db: "$rootAuthDatabase" } ]
            })
        EOJS
        echo "Creating user database: ${mongo_db_name}"
        ${pkgs.mongosh}/bin/mongosh --port ${toString mongo_port} ${mongo_db_name} >/dev/null <<-EOJS
            db.createUser({
              user: "user",
              pwd: "user_pwd",
              roles: [{role: "readWrite", db: "${mongo_db_name}" }]
            });
        EOJS
      '';
    in
    lib.mkForce "${configureScript}/bin/configure-mongodb";
}
