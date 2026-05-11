{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.garage;

  toml = pkgs.formats.toml { };
  configFile = toml.generate "garage.toml" cfg.settings;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  inherit (lib.strings) hasPrefix substring stringLength;

  stripPath = strPath: if (hasPrefix "/" strPath) then (substring 1 (stringLength strPath) strPath) else strPath;

in
{
  options.lomas.garage = {
    enable = mkEnableOption "Enable Lomas Garage";

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
      type = types.port;
      default = 3900;
      description = "Garage port";
    };

    rpcPort = mkOption {
      type = types.port;
      default = 3901;
      description = "Garage RPC port";
    };

    apiPort = mkOption {
      type = types.port;
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
            default = "${config.devenv.state}/garage/meta";
            type = types.path;
            description = "The metadata directory, put this on a fast disk (e.g. SSD) if possible.";
          };

          data_dir = mkOption {
            default = "${config.devenv.state}/garage/data";
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

  config = mkIf cfg.enable {
    packages = [
      cfg.package
      pkgs.minio-client
    ];

    env.GARAGE_CONFIG_FILE = configFile;

    processes.garage = {
      env.GARAGE_CONFIG_FILE = toString configFile;
      exec = "${lib.getExe cfg.package} server";

      # Cannot use http probe directly as /health fails when layout is not setup yet
      ready.exec = ''
        ${lib.getExe pkgs.curl} -sf \
          -H "Authorization: Bearer ${cfg.settings.admin.admin_token}" \
          http://${cfg.host}:${toString cfg.apiPort}/v2/GetClusterHealth
      '';

      before = [ "devenv:garage:configure" ];
    };

    tasks."devenv:garage:configure" = {
      env.GARAGE_CONFIG_FILE = "${config.env.GARAGE_CONFIG_FILE}";
      exec = ''
        if [ $(curl -fso /dev/null -w "%{http_code}" localhost:${toString cfg.apiPort}/health) -ne 200 ]; then
          nodeId=$(garage json-api GetClusterStatus | ${lib.getExe pkgs.jq} -r '.nodes[0].id')
          garage layout assign -z dc1 -c 1G $nodeId
          garage layout apply --version 1
        fi
      '';

      before = [ "devenv:garage:configure:bucket" ];
    };

    tasks."devenv:garage:configure:bucket" = {
      env.GARAGE_CONFIG_FILE = "${config.env.GARAGE_CONFIG_FILE}";
      exec = ''
        if ! $(garage bucket info ${cfg.bucketName} > /dev/null); then
          garage bucket create ${cfg.bucketName}
        else
          echo "${cfg.bucketName} present"
        fi

        # garage key create bucket-key
        # garage bucket allow --read --write ${cfg.bucketName} --key bucket-key

        if ! $(garage key info ${cfg.keyId} > /dev/null); then
          garage key import --yes ${cfg.keyId} ${cfg.secretKey}
        else
          echo "${cfg.keyId} present"
        fi

        if ! $(garage json-api GetBucketInfo '{"globalAlias": "${cfg.bucketName}"}' | ${lib.getExe pkgs.jq} '.keys[].accessKeyId' | grep -q ${cfg.keyId}); then
          garage bucket allow --read --write ${cfg.bucketName} --key ${cfg.keyId}
        else
          echo "${cfg.keyId} already has RW on ${cfg.bucketName}"
        fi

        mc alias set ${cfg.serviceHost} http://localhost:${toString cfg.port} ${cfg.keyId} ${cfg.secretKey} --api S3v4
        ${lib.strings.concatLines (
          (map (attrs: "mc cp ${attrs.src} ${cfg.serviceHost}/${cfg.bucketName}/${stripPath attrs.dst}") cfg.initFilesCopy)
          ++ [ "mc ls --recursive --versions ${cfg.serviceHost}/${cfg.bucketName}" ]
        )}
      '';
    };
  };

}
