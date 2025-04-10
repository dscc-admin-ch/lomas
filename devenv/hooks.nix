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
  ruff-format = {
    enable = true;
    args = [
      "--config=${env.DEVENV_ROOT}/pyproject.toml"
      "--line-length=110"
    ];
  };

}
