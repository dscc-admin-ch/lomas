{ pkgs, lib, config, inputs, ... }:

let
  inherit (builtins) readFile concatStringsSep;
  mongo_port = "27017";
  minio_port = "9090";
in
{
  # https://devenv.sh/basics/
  env.GREET = "Lomas env";

  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.mongodb-6_0
    pkgs.mongosh
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
    '' +
    # missing ?
    ''
      coverage==7.6.9
    '';
  };

  env = {
    PYTHONPATH = "${config.env.DEVENV_ROOT}/core:${config.env.DEVENV_ROOT}/server";
  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/

  ###########
  # MONGODB #
  ###########
  services.mongodb = {
    enable = true;
    package = pkgs.mongodb-6_0;
    additionalArgs = [ "--port" "${mongo_port}" ];
    initDatabaseUsername = "root";
    initDatabasePassword = "root_pwd";
  };

  tasks."mongodb:createdb" = {
    exec = "${pkgs.mongosh}/bin/mongosh 127.0.0.1:${mongo_port}/defaultdb --file ${./server/configs/mongodb_init.js}";
  };

  #########
  # MINIO #
  #########

  services.minio = let
    accessKey = "admin";
    secretKey = "admin123";
    listenAddress = "127.0.0.1:${minio_port}";
  in{
    enable = true;
    browser = false;
    inherit accessKey secretKey listenAddress;
    buckets = [ "example" ];
    afterStart = ''
      mc cp ${./server/lomas_server/tests/test_data/test_penguin.csv} myminio/example/data/test_penguin.csv
      mc cp ${./server/lomas_server/tests/test_data/metadata/penguin_metadata.yaml}  myminio/example/metadata/penguin_metadata.yaml
      mc ls --recursive --versions myminio/example
    '';
    # Configure myminio alias
    clientConfig = {
      aliases.myminio = {
        url = listenAddress;
        inherit accessKey secretKey;
        api = "S3v4";
        path = "auto";
      };
    };
  };

  # https://devenv.sh/scripts/
  enterShell = ''
    echo hello from $GREET
    echo $env
    $(which zsh &> /dev/null) && zsh
  '';

  scripts.ut.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    python -m unittest discover
    popd
  '';

  scripts.ut-coverage.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server

    # mongodb & s3 minio available
    LOMAS_TEST_MONGO_INTEGRATION=1 LOMAS_TEST_S3_INTEGRATION=1 coverage run --source=. -m unittest

    # "yaml", "basic", developer mode, "stall"
    LOMAS_TEST_MONGO_INTEGRATION=0 LOMAS_TEST_S3_INTEGRATION=0 coverage run -a --source=. -m unittest

    coverage report
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
