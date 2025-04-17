{ env, ... }:
{
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
    args = [
      "--config"
      "${env.DEVENV_ROOT}/pyproject.toml"
    ];
  };

  ruff.enable = true;

  pylint = {
    enable = true;
    after = [ "ruff" ];
    verbose = true;
    args = [
      "--rcfile"
      "${env.DEVENV_ROOT}/pyproject.toml"
      "--fail-under"
      "8"
    ];
  };

}
