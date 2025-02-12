{
  pkgs,
  lib,
  config,
  ...
}:

let
  inherit (builtins) readFile concatStringsSep toJSON;

  mongo_port = "27017";
  minio_port = "9000";
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
  env.GREET = "Lomas env";

  devcontainer.enable = true;

  packages = [
    pkgs.git
    pkgs.mongosh
  ];

  languages.python = {
    enable = true;
    uv.enable = true;
    venv.enable = true;
    venv.requirements = (
      concatStringsSep "\n" (
        map readFile [
          ./core/requirements_core.txt
          ./client/requirements_client.txt
          ./server/requirements_server.txt
          ./server/requirements_streamlit.txt
          ./requirements-dev.txt
        ]
      )
    );
  };

  env = {
    PYTHONPATH = "${config.env.DEVENV_ROOT}/core:${config.env.DEVENV_ROOT}/server";
    # LOMAS_CONFIG_PATH = "${lomas_config}";
    # LOMAS_SECRETS_PATH = "${lomas_secrets}";
  };

  ############
  # RABBITMQ #
  ############

  services.rabbitmq = {
    enable = true;
    listenAddress = "127.0.0.1";
    port = 5672;
    nodeName = "rabbit@localhost";
  };

  processes.worker = {
    exec = ''
      pushd $DEVENV_ROOT/server/lomas_server
      $UV_PROJECT_ENVIRONMENT/bin/python worker.py
      popd
    '';
    process-compose.depends_on = {
      rabbitmq.condition = "process_healthy";
      mongodb.condition = "process_healthy";
      mongodb-init-lomas.condition = "process_started";
    };
  };

  ###########
  # MONGODB #
  ###########

  services.mongodb = {
    enable = true;
    additionalArgs = [
      "--port"
      "${mongo_port}"
    ];
    initDatabaseUsername = "root";
    initDatabasePassword = "root_pwd";
  };

  processes.mongodb.process-compose = {
    readiness_probe = {
      exec.command = ''
        ${pkgs.mongosh}/bin/mongosh --quiet --eval "{ ping: 1 }" --port ${mongo_port} 2>&1 >/dev/null
      '';
      initial_delay_seconds = 5;
      period_seconds = 10;
      timeout_seconds = 5;
      success_threshold = 1;
      failure_threshold = 3;
    };
  };

  processes.mongodb-init-lomas = {
    exec = ''
      ${pkgs.mongosh}/bin/mongosh 127.0.0.1:${mongo_port}/defaultdb --file ${./server/configs/mongodb_init.js};
      tail -f /dev/null
    '';
    process-compose.depends_on."mongodb".condition = "process_healthy";
  };

  #############
  # GIT HOOKS #
  #############

  git-hooks.hooks = {
    nixfmt-rfc-style = {
      enable = true;
      args = [
        "--width"
        "120"
      ];
    };
    isort.enable = true;
    black = {
      enable = true;
      args = [
        "--line-length"
        "110"
      ];
    };
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
        "--max-line-length"
        "110"
        "--disable"
        (concatStringsSep "," [
          "fixme"
          "import-error"
          "duplicate-code"
          "too-many-lines"
          "too-many-locals"
          "no-name-in-module"
          "too-many-arguments"
          "too-few-public-methods"
          "dangerous-default-value"
          "missing-module-docstring"
          "logging-fstring-interpolation"
        ])
        "--fail-under"
        "8"
      ];
    };
  };

  #########
  # MINIO #
  #########

  services.minio =
    let
      listenAddress = "127.0.0.1:${minio_port}";
    in
    {
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
          url = "http://${listenAddress}"; # <scheme>:// is mandatory
          inherit accessKey secretKey;
          api = "S3v4";
          path = "auto";
        };
      };
    };

  enterShell = ''
    echo hello from $GREET
  '';

  scripts.ut.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    pytest .
    popd
  '';

  scripts.ut-coverage.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server

    # "basic", developer mode, "stall"
    LOMAS_TEST_S3_INTEGRATION=0 coverage run --source=. -m unittest

    # s3 minio available
    LOMAS_TEST_S3_INTEGRATION=1 coverage run -a --source=. -m unittest

    coverage report
    coverage xml -o coverage.xml

    popd
  '';

  scripts.run-linter.exec = ''
    pushd $DEVENV_ROOT
    isort .
    black .
    flake8 .
    pylint .
    pydocstringformatter .
    mypy .
    popd
  '';

  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
    ${config.scripts.ut.exec}
  '';
}
