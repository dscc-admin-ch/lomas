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

          package = mkPackageOption perSystem.config.packages "lomasService" { };

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

          externalUrl = mkOption {
            default = "http://server:${toString cfg.adminPort}";
            description = "Hostname on which Lomas can be found";
            type = types.str;
          };

          port = mkOption {
            default = 8080;
            description = "Port on which Lomas will listen for User API calls.";
            type = types.port;
          };

          adminPort = mkOption {
            default = 8081;
            description = "Port on which Lomas will listen for Admin API calls.";
            type = types.port;
          };

          # todo: default null & consequences ?
          bootstrap = mkOption {
            default = "deadbeef";
            description = "Bootstrap token to setup (admin)users;";
            type = types.str;
          };

          workerApiKey = mkOption {
            default = "workerdeadbeef";
            description = "Api Key for worker to authenticate to the server admin API";
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

          idpIssuer = mkOption {
            default = "http://dex:8080/dex";
            type = types.nullOr types.str;
          };

          dexGrpc = mkOption {
            default = "grpc://dex:50051";
            type = types.nullOr types.str;
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
            LOMAS_SERVER_bind_ip = cfg.listenAddress;
            LOMAS_SERVER_user_host_port = toString cfg.port;
            LOMAS_SERVER_admin_host_port = toString cfg.adminPort;
            LOMAS_SERVER_worker_api_key = cfg.workerApiKey;
            # Demo Setup
            LOMAS_SERVER_bootstrap = cfg.bootstrap;
            LOMAS_SERVER_authenticator__authentication_type = if (cfg.idpIssuer != null) then "oidc" else "free_pass";
            LOMAS_SERVER_authenticator__oidc_discovery_url = "${cfg.idpIssuer}/.well-known/openid-configuration";
            LOMAS_ADMIN_bootstrap = cfg.bootstrap;
            LOMAS_ADMIN_server_url = cfg.externalUrl;
            LOMAS_ADMIN_dex_config__url = cfg.dexGrpc;
            LOMAS_ADMIN_user_yaml = cfg.initUsers;
            LOMAS_ADMIN_dataset_yaml = cfg.initDatasets;
          };

          serviceConfig = {
            Type = "notify";
            ExecStart = "@${cfg.package}/bin/lomas lomas start";
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
            LOMAS_SERVER_server_host_addr = "server";
            LOMAS_SERVER_admin_host_port = toString cfg.adminPort;
            LOMAS_SERVER_authenticator__authentication_type = lib.mkDefault "free_pass";
            LOMAS_SERVER_worker_api_key = cfg.workerApiKey;
          };

          serviceConfig = {
            Type = "notify";
            ExecStart = "@${cfg.package}/bin/lomas lomas work";
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
          allowedTCPPorts = [
            cfg.port
            cfg.adminPort
          ];
        };
      };
    }
  );
}
