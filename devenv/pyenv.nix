{
  lib,
  config,
  localflake,
  ...
}:
let
  inherit (lib) types;
  cfg = config.lomas.pyenv;
in
{
  options.lomas.pyenv = {
    enable = lib.mkEnableOption "Enable Nix Python Env";
    version = lib.mkOption {
      type = types.str;
      default = "3.13";
    };
  };

  config =
    let
      pyShortVersion = lib.replaceString "." "" cfg.version;
      devshell = localflake.devShells.x86_64-linux."py${pyShortVersion}";
    in
    lib.mkIf cfg.enable {
      packages = devshell.nativeBuildInputs;

      # collect upper case ENV variables
      env = lib.filterAttrs (n: v: n == (lib.toUpper n)) devshell;

      enterShell = lib.mkAfter devshell.shellHook;
    };
}
