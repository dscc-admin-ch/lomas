{
  pkgs,
  lib,
  config,
  ...
}:

let
  inherit (lib) types;
  cfg = config.hooks;
in
{
  options.hooks = {
    enable = lib.mkEnableOption "Enable Lomas Git pre-commit hooks";

    projectConfigFile = lib.mkOption {
      type = types.nullOr types.str;
      default = null;
      example = "pyproject.toml";
      description = "path to the project config/rcfile";
    };
  };

  config = lib.mkIf cfg.enable {
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
