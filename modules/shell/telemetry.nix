{ inputs, lib, ... }:
let
  inherit (import ../_lib.nix { inherit lib; }) portStr;
in
{
  options.perSystem = inputs.flake-parts.lib.mkPerSystemOption (
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      inherit (lib)
        types
        mkPackageOption
        mkOption
        ;
      settingsFormat = pkgs.formats.yaml { };
    in
    {
      options.dev.telemetry = {

        package = mkPackageOption pkgs "opentelemetry-collector" { };

        # host = mkOption {
        #   type = types.str;
        #   default = "localhost";
        #   example = "telemetry.domain";
        #   description = "telemetry address";
        # };
        #
        # port = mkOption {
        #   type = portStr;
        #   default = 3900;
        #   description = "telemetry port";
        # };

        settings = mkOption {
          type = settingsFormat.type;
          default = { };
          description = ''
            Specify the configuration for Opentelemetry Collector in Nix.

            See <https://opentelemetry.io/docs/collector/configuration/> for available options.
          '';
        };
      };
    }
  );

  config.perSystem =
    {
      self',
      config,
      lib,
      pkgs,
      ...
    }:
    let
      cfg = config.dev.telemetry;
      unitConfig = "telemetry.service";
      settingsFormat = pkgs.formats.yaml { };
      generatedConf = settingsFormat.generate "config.yaml" cfg.settings;
      telemetry-unit = pkgs.writeText unitConfig ''
        [Unit]
        Description=Opentelemetry Collector Service Daemon

        [Service]
        Slice=lomas.slice
        Type=simple
        ExecStart=${lib.getExe cfg.package} --config=file:${generatedConf}

        [Install]
        Alias=telemetry.service
      '';
    in
    {
      packages.telemetry-service = telemetry-unit;

      make-shell.imports = [
        {
          shellHook = ''
            install -C -Dm644 -T ${self'.packages.telemetry-service} deploy/systemd/${unitConfig}
          '';
        }
      ];
    };
}
