{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.lomas.hooks;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;
in
{
  options.lomas.hooks = {
    enable = mkEnableOption "Enable Lomas Git pre-commit hooks";

    projectConfigFile = mkOption {
      type = types.nullOr types.str;
      default = null;
      example = "pyproject.toml";
      description = "path to the project config/rcfile if any";
    };
  };

  config = mkIf cfg.enable {
    git-hooks.hooks = {
      trim-trailing-whitespace.enable = true;

      nbstripout = {
        enable = true;
        name = "nbstripout";
        description = "strip output from Jupyter and IPython notebooks";
        files = "\\.ipynb$";
        entry = "${pkgs.nbstripout}/bin/nbstripout";
        args = [
          "--keep-output"
          "--drop-empty-cells"
        ];
      };

      nixfmt-rfc-style = {
        enable = true;
        args = [
          "--width"
          "120"
        ];
      };

      black = {
        enable = true;
        before = [ "ruff" ];
        args = lib.optionals (cfg.projectConfigFile != null) [
          "--config"
          "${cfg.projectConfigFile}"
        ];
      };

      ruff.enable = true;

      pylint = {
        enable = true;
        after = [ "ruff" ];
        verbose = true;
        args =
          [
            "--fail-under"
            "8"
          ]
          ++ (lib.optionals (cfg.projectConfigFile != null) [
            "--rcfile"
            "${cfg.projectConfigFile}"
          ]);
      };
    };
  };
}
