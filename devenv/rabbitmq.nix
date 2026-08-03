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

    prometheusPort = mkOption {
      type = types.int;
      default = 15692;
      description = "RabbitMQ Prometheus metrics TCP port";
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

}
