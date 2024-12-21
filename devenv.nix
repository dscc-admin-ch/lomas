{ pkgs, lib, config, ... }:

let
  inherit (builtins) readFile concatStringsSep toJSON;

  mongo_port = "27017";
  minio_port = "9090";
  accessKey = "admin";
  secretKey = "admin123";

  lomas_config = pkgs.writeText "test_config.yaml" (toJSON {
    runtime_args = {
        settings = {
          develop_mode = true;
          submit_limit = 300;
          server = {
            host_ip = "localhost";
            host_port = "64080"; # 80 is privileged
            log_level = "info";
            reload = true;
            workers = 1;
            time_attack = {
              method = "stall";
              magnitude = 1;
            };
          };
          admin_database = {
            db_type = "yaml";
            db_file = "${./server/lomas_server/tests/test_data/local_db_file.yaml}";
          };
          dp_libraries = {
            opendp = {
              contrib = true;
              floating_point = true;
              honest_but_curious = false;
            };
          };
        };
      };
    });

  lomas_secrets = pkgs.writeText "test_secrets.yaml" (toJSON {
    admin_database = {
      password = "user_pwd";
      username = "user";
    };
    private_db_credentials = [
      {
        credentials_name = "local_minio";
        db_type = "S3_DB";
        access_key_id = accessKey;
        secret_access_key = secretKey;
      }
    ];
  });
in
{
  # https://devenv.sh/basics/
  env.GREET = "Lomas env";

  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.mongodb-6_0
    pkgs.mongosh
    pkgs.oauth2-proxy
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
    LOMAS_CONFIG_PATH = "${lomas_config}";
    LOMAS_SECRETS_PATH = "${lomas_secrets}";
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
