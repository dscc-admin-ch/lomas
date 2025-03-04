{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

let
  inherit (builtins) readFile concatStringsSep toJSON;

  mongo_port = 27017;
  minio_port = 19000;
  accessKey = "admin";
  secretKey = "admin123";
  rabbitmq_port = 5672;
  rabbitmq_mgmt_port = 15672; # spin the management interface http://localhost:15672 guest/guest
  mongo_db_name = "defaultdb";
  lomas_port = 48080;

  lomas_config = pkgs.writeText "test_config.yaml" (toJSON {
    runtime_args = {
      settings = {
        develop_mode = false;
        submit_limit = 300;
        server = {
          host_ip = "0.0.0.0";
          host_port = lomas_port;
          log_level = "info";
          reload = true;
          workers = 1;
          time_attack = {
            method = "jitter";
            magnitude = 1;
          };
        };
        admin_database = {
          db_type = "mongodb";
          address = "127.0.0.1";
          port = mongo_port;
          db_name = mongo_db_name;
          max_pool_size = 100;
          min_pool_size = 2;
          max_connecting = 2;
        };
        dp_libraries = {
          opendp = {
            contrib = true;
            floating_point = true;
            honest_but_curious = true;
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

  lomas_dashboard = pkgs.writeText "dashboard.yaml" (toJSON {
    server_service = "http://localhost:${toString lomas_port}";
    server_url = "CakeMightBeALie.ch";
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
    LOMAS_CONFIG_PATH = "${lomas_config}";
    LOMAS_SECRETS_PATH = "${lomas_secrets}";
    LOMAS_DASHBOARD_CONFIG_PATH = "${lomas_dashboard}";
  };

  ############
  # RABBITMQ #
  ############

  services.rabbitmq = {
    enable = true;
    listenAddress = "127.0.0.1";
    port = rabbitmq_port;
    nodeName = "rabbit@localhost";
    managementPlugin = {
      enable = true;
      port = rabbitmq_mgmt_port;
    };
  };

  processes.worker = {
    exec = ''
      pushd $DEVENV_ROOT/server/lomas_server
      $UV_PROJECT_ENVIRONMENT/bin/python worker.py
      popd
    '';
    process-compose = {
      depends_on.rabbitmq.condition = "process_healthy";
      replicas = 2;
    };
  };

  ###########
  # MONGODB #
  ###########

  # Current SSPL license of MongoDB is, debatably, not tagged as 'free' in upstream nixpkgs
  services.mongodb =
    let
      pkgs_sspl = import inputs.nixpkgs {
        inherit (pkgs.stdenv) system;
        config = pkgs.config // {
          allowlistedLicenses = [ lib.licenses.sspl ];
        };
      };
    in
    {
      enable = true;
      package = pkgs_sspl.mongodb-ce;
      additionalArgs = [
        "--port"
        (toString mongo_port)
      ];
      initDatabaseUsername = "root";
      initDatabasePassword = "root_pwd";
    };

  processes.mongodb.process-compose = {
    readiness_probe = {
      exec.command = ''
        ${pkgs.mongosh}/bin/mongosh --quiet --eval "{ ping: 1 }" --port ${toString mongo_port} 2>&1 >/dev/null
      '';
      initial_delay_seconds = 3;
      period_seconds = 10;
      timeout_seconds = 5;
      success_threshold = 1;
      failure_threshold = 3;
    };
  };

  processes.mongodb-configure.process-compose.depends_on.mongodb.condition = "process_healthy";
  processes.mongodb-configure.exec =
    let
      configureScript = pkgs.writeShellScriptBin "configure-mongodb" ''
        set -euo pipefail
        echo "Creating initial user"
        rootAuthDatabase="admin"
        ${pkgs.mongosh}/bin/mongosh --port ${toString mongo_port} "$rootAuthDatabase" >/dev/null <<-EOJS
            db.createUser({
                user: "${config.services.mongodb.initDatabaseUsername}",
                pwd: "${config.services.mongodb.initDatabasePassword}",``
                roles: [ { role: 'root', db: "$rootAuthDatabase" } ]
            })
        EOJS
        echo "Creating user database: ${mongo_db_name}"
        ${pkgs.mongosh}/bin/mongosh --port ${toString mongo_port} ${mongo_db_name} >/dev/null <<-EOJS
            db.createUser({
              user: "user",
              pwd: "user_pwd",
              roles: [{role: "readWrite", db: "${mongo_db_name}" }]
            });
        EOJS
      '';
    in
    lib.mkForce "${configureScript}/bin/configure-mongodb";

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
      listenAddress = "127.0.0.1:${toString minio_port}";
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

  scripts.ut-coverage.exec =
    let
      working_dir = "$DEVENV_ROOT/server/lomas_server";
      pc-config-patch = pkgs.writeText "pc-coverage-disable-worker.yaml" (toJSON {
        processes = {
          # patch/override worker definition to force 1 instance and run coverage on it
          worker = {
            inherit working_dir;
            replicas = 1;
            command = "$UV_PROJECT_ENVIRONMENT/bin/coverage run --source=. -p worker.py";
          };
          # Add this ad-hoc pytest process to be run in foreground whilst ensuring
          # all background dependencies
          pytest-cov = {
            inherit working_dir;
            command = "pytest --no-cov-on-fail --cov . -k 'not admin_cli'";
            depends_on = {
              worker.condition = "process_started";
              minio.condition = "process_started";
              mongodb.condition = "process_started";
              mongodb-configure.condition = "process_completed_successfully";
            };
            # We terminate the whole process-compose at the end of this task
            availability.exit_on_end = true;
          };
        };
      });
    in
    ''
      pushd ${working_dir}
      echo "Running coverage with patched process-compose config (${pc-config-patch})"
      process-compose run pytest-cov -f $PC_CONFIG_FILES -f ${pc-config-patch}
      pytest_return=$?

      if [ $pytest_return -eq 0 ]; then
        echo "✅ test success -> building coverage"
        # these per-process coverages are generated by coverage run -p <...>
        coverage combine -a .coverage.*
        coverage report
        coverage xml -o coverage.xml
      fi

      popd
      exit $pytest_return
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

  scripts.run-jupyter.exec = ''
    pushd $DEVENV_ROOT/client
    jupyter notebook --ip 0.0.0.0 --no-browser --allow-root
    popd
  '';

  scripts.run-fastapi.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    fastapi dev --port ${toString lomas_port} app.py
    popd
  '';

  scripts.run-streamlit.exec = ''
    pushd $DEVENV_ROOT/server
    streamlit run lomas_server/administration/dashboard/about.py
    popd
  '';

  scripts.py-build.exec = ''
    pushd $DEVENV_ROOT
    uv build --sdist core
    uv build --sdist client
    uv build --sdist server
    popd
  '';

  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
    ${config.scripts.ut.exec}
  '';
}
