{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.rabbitmq;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  ipAddress = lib.mkOptionType {
    name = "ipAddress";
    check = x: types.str.check x && builtins.match "[.0-9:A-Fa-f]+" x != null;
    merge = types.str.merge;
    description = "IPv4 or IPv6 address";
    descriptionClass = "conjunction";
  };
in
{
  options.lomas.rabbitmq = {
    enable = mkEnableOption "Enable Lomas RabbitMQ";

    host = mkOption {
      type = types.str;
      default = "localhost";
      example = "rabbitmq.domain";
      description = "RabbitMQ address";
    };

    bindAddr = mkOption {
      type = ipAddress;
      default = "127.0.0.1";
      example = "0.0.0.0";
      description = "RabbitMQ Erlang server binding IP";
    };

    port = mkOption {
      type = types.int;
      default = 5672;
      description = "RabbitMQ port";
    };

    nodeName = mkOption {
      type = types.str;
      example = "rabbit@localhost";
      description = "RabbitMQ Node name";
    };

    portManagement = mkOption {
      type = types.int;
      default = 15672;
      description = "RabbitMQ management UI and HTTP API";
    };

    user = mkOption {
      type = types.str;
      description = "RabbitMQ default user name";
    };

    password = mkOption {
      type = types.str;
      description = "RabbitMQ default user password";
    };

    heartbeat = mkOption {
      type = types.int;
      default = 60;
      description = "RabbitMQ Heartbeat (seconds) (https://www.rabbitmq.com/docs/heartbeats)";
    };
  };

  config = mkIf cfg.enable {
    services.rabbitmq = {
      enable = true;
      listenAddress = cfg.bindAddr;
      port = cfg.port;
      nodeName = cfg.nodeName;
      managementPlugin = {
        enable = true;
        port = cfg.portManagement;
      };
      configItems = {
        "default_user" = cfg.user;
        "default_pass" = cfg.password;
        "heartbeat" = toString cfg.heartbeat;
      };
    };

    # official documentation
    # a TCP port check on the AMQP port as the readinessProbe and no livenessProbe at all.
    # This should be considered the best practice.
    processes.rabbitmq.ready = {
      exec = lib.mkForce "${pkgs.netcat}/bin/nc -z -v -w 5 ${cfg.host} ${toString cfg.port}";
    };

  };

}
