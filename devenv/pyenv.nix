{
  pkgs,
  lib,
  config,
  pyproject-nix,
  uv2nix,
  pyproject-build-systems,
  ...
}:
let
  cfg = config.lomas.pyenv;

  pyEnv = import ./lib.nix {
    inherit
      pkgs
      lib
      uv2nix
      pyproject-nix
      pyproject-build-systems
      ;
    python = cfg.package;
    workspaceRoot = ../.;
  };
in
{
  options.lomas.pyenv = {
    enable = lib.mkEnableOption "Enable Nix Python Env";
    package = lib.mkPackageOption pkgs "python3" { };
  };

  config = lib.mkIf cfg.enable {
    packages = [
      pyEnv.virtualenv
      pkgs.uv
    ];

    env = {
      UV_NO_SYNC = "1";
      UV_PYTHON = pyEnv.pythonSet.python.interpreter;
      UV_PYTHON_DOWNLOADS = "never";
      # some editor uses this to find py sources
      VIRTUAL_ENV = ".devenv/profile";
    };

    enterShell = lib.mkAfter ''
      unset PYTHONPATH
      export REPO_ROOT=$(git rev-parse --show-toplevel)
    '';

    outputs = {
      lomas-dev-env = pyEnv.virtualenv;
      lomas-env = pyEnv.lomasEnv;
    };
  };
}
