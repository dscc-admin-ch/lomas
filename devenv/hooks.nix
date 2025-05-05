{ pkgs, env, ... }:
{
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
