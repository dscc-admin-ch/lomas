{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomasMinio;

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
  options.lomasMinio = {
    enable = mkEnableOption "Enable Lomas Minio";

    host = mkOption {
      type = types.str;
      default = "localhost";
      example = "minio.domain";
      description = "Minio address";
    };

    port = mkOption {
      type = types.int;
      description = "Minio port";
    };

    console_port = mkOption {
      type = types.int;
      description = "Minio Console port";
    };

    rootUser = mkOption {
      type = types.str;
      default = "admin";
      example = "admin";
      description = "Minio Admin Username";
    };

    rootPassword = mkOption {
      type = types.str;
      description = "Minio Admin Password";
    };

    serviceHost = mkOption {
      type = types.str;
      default = "myminio";
      description = "S3-compatible service host(name)";
    };

    bucketName = mkOption {
      type = types.str;
      default = "example";
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
  };

  config = mkIf cfg.enable {
    services.minio = {
      enable = true;
      browser = false;
      listenAddress = "${cfg.host}:${toString cfg.port}";
      accessKey = cfg.rootUser;
      secretKey = cfg.rootPassword;
      buckets = lib.singleton cfg.bucketName;
      afterStart = lib.strings.concatLines (
        (map (attrs: "mc cp ${attrs.src} ${cfg.serviceHost}/${cfg.bucketName}/${stripPath attrs.dst}") cfg.initFilesCopy)
        ++ [ "mc ls --recursive --versions ${cfg.serviceHost}/${cfg.bucketName}" ]
      );

      clientConfig = {
        aliases.${cfg.serviceHost} = {
          url = "http://${cfg.host}:${toString cfg.port}"; # <scheme>:// is mandatory
          accessKey = cfg.rootUser;
          secretKey = cfg.rootPassword;
          api = "S3v4";
          path = "auto";
        };
      };
    };
  };

}
