{ pkgs, lib, config, inputs, ... }:

let
inherit (builtins) readFile concatStringsSep;
in
{
  # https://devenv.sh/basics/
  env.GREET = "Lomas env";

  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.mongodb-6_0
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    venv.enable = true;
    venv.requirements = (
      concatStringsSep "\n" (
        map readFile [
        ./core/requirements_core.txt
        ./client/requirements_client.txt
        ./server/requirements_server.txt
        ./server/requirements_streamlit.txt
      ])
    ) +
    # Linter
    ''
      isort==5.13.2
      black==24.4.2
      flake8-pyproject==1.2.3
      mypy==1.10.0
      pylint==3.1.0
      pydocstringformatter==0.7.3
    '';
  };

  env = {
    PYTHONPATH = "${./core}:${./server}";
  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  enterShell = ''
    echo hello from $GREET
    exec zsh
  '';

  scripts.ut.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    python -m unittest discover
    popd
  '';

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
    ${config.scripts.ut.exec}
  '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
