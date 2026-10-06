{ pkgs, lib, ... }:
let
  inherit (lib.strings) hasPrefix substring stringLength;
  stripPath = strPath: if (hasPrefix "/" strPath) then (substring 1 (stringLength strPath) strPath) else strPath;
  admin_data_dir = "./server/data";
in
{
  garage-service =
    let
      bucketName = "bucket";
      # GK + 12 hex-encoded bytes
      keyId = "GK0123456789abcdefdeadbeef";
      # 32 hex-encoded bytes
      secretKey = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
      serviceHost = "mygarage";
      port = 3900;
      apiPort = 3903;
      initFilesCopy = [
        {
          src = builtins.path {
            name = "penguinData";
            path = ../../server/lomas_server/tests/test_data/test_penguin.csv;
          };
          dst = "/data/test_penguin.csv";
        }
        {
          src = builtins.path {
            name = "penguinMetadata";
            path = ../../server/lomas_server/tests/test_data/metadata/penguin_metadata.json;
          };
          dst = "/metadata/penguin_metadata.json";
        }
        {
          src = builtins.path {
            name = "Titanic";
            path = ../../server/data/datasets/titanic.csv;
          };
          dst = "/data/titanic.csv";
        }
        {
          src = builtins.path {
            name = "TitanicMetadata";
            path = ../../server/data/collections/metadata/titanic_metadata.json;
          };
          dst = "/metadata/titanic_metadata.json";
        }
      ];
      format = pkgs.formats.toml { };
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
          api_bind_addr = "0.0.0.0:${toString apiPort}";
          admin_token = "e3640a659b59c6a6b06c0820a2bd0380aa12124b61000aee7af684d10aab7fa0";
        };

        metrics_require_token = true;
        metrics_token = "ddd02920a2431ad2d8fb77207f2933e775873c2461894a443c61776a3db854fd";
      };
      garageConfig = format.generate "garage.toml" settings;
      garageInit = pkgs.writeShellApplication {
        name = "garage-init";
        runtimeInputs = [
          pkgs.coreutils # sleep
          pkgs.gnugrep
          pkgs.curl
          pkgs.jq
          pkgs.getent # hidden minio req
          pkgs.minio-client
          pkgs.garage_2
        ];
        runtimeEnv = { };
        text = ''
          function garageHealthEndpoint() {
            curl -f -H 'Authorization: Bearer ${settings.admin.admin_token}' \
              'http://0.0.0.0:${toString apiPort}/v1/health' 2>/dev/null
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

          if ! $GARAGE bucket info ${bucketName} > /dev/null; then
            $GARAGE bucket create ${bucketName}
          else
            echo "${bucketName} present"
          fi

          # $GARAGE key create bucket-key
          # $GARAGE bucket allow --read --write ${bucketName} --key bucket-key

          if ! $GARAGE key info ${keyId} > /dev/null; then
            $GARAGE key import --yes ${keyId} ${secretKey}
          else
            echo "${keyId} present"
          fi

          if ! ($GARAGE json-api GetBucketInfo '{"globalAlias": "${bucketName}"}' | jq '.keys[].accessKeyId' | grep -q ${keyId}); then
            $GARAGE bucket allow --read --write ${bucketName} --key ${keyId}
          else
            echo "${keyId} already has RW on ${bucketName}"
          fi

          # mini-client is absolute garbage (-C/--config-dir still requires $HOME)
          HOME=/var/tmp/mc mc alias set ${serviceHost} http://localhost:${toString port} ${keyId} ${secretKey} --api S3v4
          ${lib.strings.concatLines (
            (map (attrs: "HOME=/var/tmp/mc mc cp ${attrs.src} ${serviceHost}/${bucketName}/${stripPath attrs.dst}") initFilesCopy)
            ++ [ "HOME=/var/tmp/mc mc ls --recursive --versions ${serviceHost}/${bucketName}" ]
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
        ExecStart=${lib.getExe pkgs.garage_2} -c ${garageConfig} server
        ExecStartPost=${lib.getExe garageInit}
      '';
    in
    pkgs.portableService {
      pname = "garage";
      version = "1";
      units = [ garage-unit ];
    };
}
