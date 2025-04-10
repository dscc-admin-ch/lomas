{ env, ... }:
{
  nixfmt-rfc-style = {
    enable = true;
    args = [
      "--width"
      "120"
    ];
  };

  # linter: ruff check
  ruff.enable = true;

  # formatter: ruff format
  ruff-format.enable = true;

  # TODO: add flake8-pyproject inside this context
  # or switch to ruff ?
  flake8 = {
    enable = true;
    args = [
      "--max-line-length"
      "110"
      "--ignore"
      "E501,W503"
    ];
  };

  pylint = {
    enable = true;
    verbose = true;
    args = [
      "--rcfile"
      "${env.DEVENV_ROOT}/pyproject.toml"
      "--fail-under"
      "8"
    ];
  };

}
