{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.garage;

  toml = pkgs.formats.toml { };

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
      pkgs.minio-client
    ];

    services.garage = {
      enable = true;
      buckets = [ cfg.bucketName ];
      rpcSecret = "00ae3c92972e91116f2612fb96ab64c963c2f7b163cab376569ec3e9be179d2d";
      adminToken = "e3640a659b59c6a6b06c0820a2bd0380aa12124b61000aee7af684d10aab7fa0";
      adminAddress = "0.0.0.0:${toString cfg.apiPort}";
      s3Address = "0.0.0.0:${toString cfg.port}";
      replicationFactor = cfg.settings.replication_factor;

      extraConfig = ''
        metrics_require_token = true
        metrics_token = "ddd02920a2431ad2d8fb77207f2933e775873c2461894a443c61776a3db854fd"
      '';

      afterStart = ''
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
