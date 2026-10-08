{ inputs, ... }:
{
  options.perSystem = inputs.flake-parts.lib.mkPerSystemOption (
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      portStr = with lib.types; coercedTo port toString str;
      toml = pkgs.formats.toml { };
      inherit (lib)
        types
        mkOption
        ;
    in
    {
      options.dev.garage = {
        package = mkOption {
          type = types.package;
          default = pkgs.garage_2;
        };

        host = mkOption {
          type = types.str;
          default = "localhost";
          example = "garage.domain";
          description = "Garage address";
        };

        port = mkOption {
          type = portStr;
          default = 3900;
          description = "Garage port";
        };

        rpcPort = mkOption {
          type = portStr;
          default = 3901;
          description = "Garage RPC port";
        };

        apiPort = mkOption {
          type = portStr;
          default = 3903;
          description = "Garage Admin API port";
        };

        keyId = mkOption {
          type = types.str;
          description = "Garage Bucket key Id";
        };

        secretKey = mkOption {
          type = types.str;
          description = "Garage Bucket key secret";
        };

        serviceHost = mkOption {
          type = types.str;
          default = "mygarage";
          description = "S3-compatible service host(name)";
        };

        bucketName = mkOption {
          type = types.str;
          default = "bucket";
          description = "Name of the simulated Bucket";
        };

        initFilesCopy = mkOption {
          type = types.listOf (
            types.submodule {
              options = {
                src = mkOption { type = types.path; };
                dst = mkOption { type = types.str; };
              };
            }
          );
        };

        settings = mkOption {
          description = "Garage configuration, see <https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/> for reference.";
          type = types.submodule {
            freeformType = toml.type;
            options = {
              metadata_dir = mkOption {
                default = "/var/lib/garage/meta";
                type = types.path;
                description = "The metadata directory, put this on a fast disk (e.g. SSD) if possible.";
              };

              data_dir = mkOption {
                default = "/var/lib/garage/data";
                example = [
                  {
                    path = "/var/lib/garage/data";
                    capacity = "2T";
                  }
                ];
                type = with types; either path (listOf attrs);
                description = ''
                  The directory in which Garage will store the data blocks of objects. This folder can be placed on an HDD.
                  Since v0.9.0, Garage supports multiple data directories, refer to <https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/#data_dir> for the exact format.
                '';
              };

              replication_factor = mkOption {
                default = 1;
                type = types.ints.positive;
              };
            };
          };
        };
      };
    }
  );

  config.perSystem =
    {
      config,
      lib,
      pkgs,
      ...
    }:
    {
      packages.garage-service =
        let
          cfg = config.dev.garage;
          inherit (lib.strings) hasPrefix substring stringLength;
          stripPath = strPath: if (hasPrefix "/" strPath) then (substring 1 (stringLength strPath) strPath) else strPath;
          settings = {
            metadata_dir = "/var/tmp/garage/meta";
            data_dir = "/var/tmp/garage/data";
            db_engine = "lmdb";

            replication_factor = 1;

            rpc_bind_addr = "[::]:3901";
            rpc_public_addr = "127.0.0.1:3901";
            rpc_secret = "00ae3c92972e91116f2612fb96ab64c963c2f7b163cab376569ec3e9be179d2d";

            s3_api = {
              s3_region = "us-east-1";
              api_bind_addr = "0.0.0.0:3900";
            };

            admin = {
              api_bind_addr = "0.0.0.0:${cfg.apiPort}";
              admin_token = "e3640a659b59c6a6b06c0820a2bd0380aa12124b61000aee7af684d10aab7fa0";
            };

            metrics_require_token = true;
            metrics_token = "ddd02920a2431ad2d8fb77207f2933e775873c2461894a443c61776a3db854fd";
          };
          garageConfig = (pkgs.formats.toml { }).generate "garage.toml" settings;
          garageInit = pkgs.writeShellApplication {
            name = "garage-init";
            runtimeInputs = [
              cfg.package
              pkgs.coreutils # sleep
              pkgs.gnugrep
              pkgs.curl
              pkgs.jq
              pkgs.getent # hidden minio req
              pkgs.minio-client
            ];
            runtimeEnv = { };
            text = ''
              function garageHealthEndpoint() {
                curl -f -H 'Authorization: Bearer ${settings.admin.admin_token}' \
                  'http://0.0.0.0:${cfg.apiPort}/v1/health' 2>/dev/null
              }

              GARAGE="garage -c ${garageConfig}"

              until garageHealthEndpoint; do
                echo "Garage not ready, waiting..."
                sleep 1
              done

              echo "Garage ready."
              echo "Configuring layout ..."
              # Apply the cluster layout once. Garage rejects S3 traffic until at
              # least one node has a role, so this step is mandatory before the
              # buckets can be touched.
              if $GARAGE status 2>/dev/null | grep -q "NO ROLE ASSIGNED"; then
                NODE_ID=$($GARAGE node id 2>/dev/null | cut -d@ -f1)
                $GARAGE layout assign -z dc1 -c 1G "$NODE_ID"
                $GARAGE layout apply --version 1
              fi

              if ! $GARAGE bucket info ${cfg.bucketName} > /dev/null; then
                $GARAGE bucket create ${cfg.bucketName}
              else
                echo "${cfg.bucketName} present"
              fi

              # $GARAGE key create bucket-key
              # $GARAGE bucket allow --read --write ${cfg.bucketName} --key bucket-key

              if ! $GARAGE key info ${cfg.keyId} > /dev/null; then
                $GARAGE key import --yes ${cfg.keyId} ${cfg.secretKey}
              else
                echo "${cfg.keyId} present"
              fi

              if ! ($GARAGE json-api GetBucketInfo '{"globalAlias": "${cfg.bucketName}"}' | jq '.keys[].accessKeyId' | grep -q ${cfg.keyId}); then
                $GARAGE bucket allow --read --write ${cfg.bucketName} --key ${cfg.keyId}
              else
                echo "${cfg.keyId} already has RW on ${cfg.bucketName}"
              fi

              # mini-client is absolute garbage (-C/--config-dir still requires $HOME)
              HOME=/var/tmp/mc mc alias set ${cfg.serviceHost} http://localhost:${cfg.port} ${cfg.keyId} ${cfg.secretKey} --api S3v4
              ${lib.strings.concatLines (
                (map (
                  attrs: "HOME=/var/tmp/mc mc cp ${attrs.src} ${cfg.serviceHost}/${cfg.bucketName}/${stripPath attrs.dst}"
                ) cfg.initFilesCopy)
                ++ [ "HOME=/var/tmp/mc mc ls --recursive --versions ${cfg.serviceHost}/${cfg.bucketName}" ]
              )}
            '';
          };
          garage-unit = pkgs.writeText "garage.service" ''
            [Unit]
            Description=S3 object store
            Documentation=https://garagehq.deuxfleurs.fr/documentation

            [Service]
            Type=simple
            # Share /tmp, /var/tmp with host
            PrivateTmp=true
            ExecStart=${lib.getExe cfg.package} -c ${garageConfig} server
            ExecStartPost=${lib.getExe garageInit}
          '';
        in
        pkgs.portableService {
          pname = "garage";
          version = "1";
          units = [ garage-unit ];
        };

    };

}
