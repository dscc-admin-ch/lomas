{ moduleWithSystem, ... }:
# moduleWithSystem: A function that brings the perSystem module arguments.
# This allows a module to reference the defining flake without introducing global variables.
{
  flake.nixosModules.lomas = moduleWithSystem (
    perSystem@{ config, ... }: # to allow perSystem.config.<...>
    nioxs@{
      config,
      lib,
      pkgs,
      ...
    }:
    let
      cfg = config.services.lomas;

      inherit (lib)
        mkPackageOption
        mkEnableOption
        mkOption
        mkIf
        types
        ;
    in
    {
      imports = [ ];

      options = {
        services.lomas = {
          enable = mkEnableOption "Whether to enable Lomas Server.";

          package = mkPackageOption perSystem.config.packages "lomasServerApp" { };

          workerOnly = mkOption {
            default = false;
            description = "Whether to setup only for Worker(s) and don't start a full Server";
            type = types.bool;
          };

          listenAddress = mkOption {
            default = "127.0.0.1";
            type = types.str;
          };

          openFirewall = mkOption {
            default = false;
            description = "Whether to open the necessary port in the firewall for lomas.";
            type = types.bool;
          };

          port = mkOption {
            default = 8080;
            description = "Port on which Lomas will listen for API calls.";
            type = types.port;
          };

          # todo: default null & consequences ?
          bootstrap = mkOption {
            default = "deadbeef";
            description = "Bootstrap token to setup (admin)users;";
            type = types.str;
          };

          amqpUrl = mkOption {
            default = "amqp://rabbitmq:5672";
            type = types.str;
          };

          amqpUsername = mkOption {
            default = "";
            type = types.str;
          };

          amqpPassword = mkOption {
            default = "";
            type = types.str;
          };

          dataDir = mkOption {
            type = types.path;
            default = "/var/lib/lomas";
            description = "The Lomas home directory used to store all data.";
          };

          initUsers = mkOption {
            default = null;
            # todo: better type
            type = types.nullOr types.path;
          };

          initDatasets = mkOption {
            default = null;
            # todo: better type
            type = types.nullOr types.path;
          };

          initDemoSetup = mkOption {
            default = (cfg.initUsers != null) && (cfg.initDatasets != null);
            description = "Run the `demo-setup` script loading initial users and datasets";
            type = types.bool;
          };

        };
      };

      ### implementation
      config = mkIf cfg.enable {
        users = {
          users.lomas = {
            description = "Lomas server user";
            home = cfg.dataDir;
            isNormalUser = true;
            createHome = true;
            group = "lomas";
          };
          groups.lomas = { };
        };

        environment.systemPackages = [ cfg.package ];

        systemd.services.lomas = mkIf (!cfg.workerOnly) {
          description = "Lomas Server";

          wantedBy = [ "multi-user.target" ];
          after = [ "network.target" ];
          wants = [ "network.target" ];

          path = [
            cfg.package
            pkgs.coreutils
          ];

          environment = {
            LOMAS_SERVICE_server__host_port = toString cfg.port;
            LOMAS_SERVICE_server__host_ip = cfg.listenAddress;
            # Demo Setup
            LOMAS_SERVICE_bootstrap = cfg.bootstrap;
            LOMAS_SERVICE_authenticator__authentication_type = "oidc";
            LOMAS_SERVICE_authenticator__oidc_discovery_url = "http://dex:8080/dex/.well-known/openid-configuration";
            LOMAS_ADMIN_bootstrap = cfg.bootstrap;
            LOMAS_ADMIN_server_url = "http://server:8080";
            LOMAS_ADMIN_dex_config__url = "grpc://dex:50051";
            LOMAS_ADMIN_user_yaml = cfg.initUsers;
            LOMAS_ADMIN_dataset_yaml = cfg.initDatasets;
            LOMAS_SERVICE_amqp__url = cfg.amqpUrl;
            LOMAS_SERVICE_amqp__username = cfg.amqpUsername;
            LOMAS_SERVICE_amqp__password = cfg.amqpPassword;
          };

          serviceConfig = {
            Type = "notify";
            ExecStart = "@${cfg.package}/bin/lomas-serve lomas-serve";
            ExecStartPost = mkIf cfg.initDemoSetup "${cfg.package}/bin/lomas-demo-setup";
            User = "lomas";
            Group = "lomas";
            LogsDirectory = "lomas";
            WorkingDirectory = cfg.dataDir;
            Restart = "always";
            RestartSec = "10";
            TimeoutStartSec = "3600";

            # Service hardening
            CapabilityBoundingSet = [ ];
            DevicePolicy = "closed";
            LockPersonality = true;
            NoNewPrivileges = true;
            PrivateDevices = true;
            PrivateTmp = true;
            ProcSubset = "pid";
            ProtectClock = true;
            ProtectControlGroups = true;
            ProtectHome = true;
            ProtectHostname = true;
            ProtectKernelLogs = true;
            ProtectKernelModules = true;
            ProtectKernelTunables = true;
            ProtectProc = "invisible";
            ProtectSystem = "strict";
            RemoveIPC = true;
            RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
            RestrictNamespaces = true;
            RestrictRealtime = true;
            RestrictSUIDSGID = true;
            SystemCallArchitectures = "native";
            SystemCallFilter = [
              "@system-service"
              "~@privileged"
            ];
            UMask = "0077";
          };
        };

        systemd.services."lomas-worker@" = {
          description = "Lomas Worker";

          wantedBy = [ "multi-user.target" ];
          after = [ "network.target" ];
          wants = [ "network.target" ];

          path = [
            cfg.package
            pkgs.coreutils
          ];

          environment = {
            LOMAS_SERVICE_authenticator__authentication_type = lib.mkDefault "free_pass";
            LOMAS_SERVICE_amqp__url = cfg.amqpUrl;
            LOMAS_SERVICE_amqp__username = cfg.amqpUsername;
            LOMAS_SERVICE_amqp__password = cfg.amqpPassword;
          };

          serviceConfig = {
            Type = "notify";
            ExecStart = "@${cfg.package}/bin/lomas-work worker-%i";
            User = "lomas";
            Group = "lomas";
            LogsDirectory = "lomas";
            WorkingDirectory = cfg.dataDir;
            Restart = "always";
            RestartSec = "10";
            TimeoutStartSec = "3600";

            # Service hardening
            CapabilityBoundingSet = [ ];
            DevicePolicy = "closed";
            LockPersonality = true;
            NoNewPrivileges = true;
            PrivateDevices = true;
            PrivateTmp = true;
            ProcSubset = "pid";
            ProtectClock = true;
            ProtectControlGroups = true;
            ProtectHome = true;
            ProtectHostname = true;
            ProtectKernelLogs = true;
            ProtectKernelModules = true;
            ProtectKernelTunables = true;
            ProtectProc = "invisible";
            ProtectSystem = "strict";
            RemoveIPC = true;
            RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
            RestrictNamespaces = true;
            RestrictRealtime = true;
            RestrictSUIDSGID = true;
            SystemCallArchitectures = "native";
            SystemCallFilter = [
              "@system-service"
              "~@privileged"
            ];
            UMask = "0077";
          };
        };

        networking.firewall = mkIf cfg.openFirewall {
          allowedTCPPorts = [ cfg.port ];
        };
      };
    }
  );
}
