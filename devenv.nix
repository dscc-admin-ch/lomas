{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

let
  inherit (builtins) readFile concatStringsSep;
  toYAML = lib.generators.toYAML { };

  mongo_port = 27017;
  minio_port = 19000;
  accessKey = "admin";
  secretKey = "admin123";
  rabbitmq_port = 5672;
  rabbitmq_mgmt_port = 15672; # spin the management interface http://localhost:15672 guest/guest
  mongo_db_name = "defaultdb";
  lomas_port = 48080;
  postgres_addr = "localhost";
  postgres_port = 5432;
  kc_https_port = 4443;
  kc_http_port = 4442;
  kc_management_port = 4441;

  lomas_config = pkgs.writeText "test_config.yaml" (toYAML {
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

  lomas_secrets = pkgs.writeText "test_secrets.yaml" (toYAML {
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

  lomas_dashboard = pkgs.writeText "dashboard.yaml" (toYAML {
    server_service = "http://localhost:${toString lomas_port}";
    server_url = "CakeMightBeALie.ch";
  });
in
{

  # Environment variable available inside devenv
  env = {
    GREET = "Lomas env";
    PYTHONPATH = "${config.env.DEVENV_ROOT}/core:${config.env.DEVENV_ROOT}/server:${config.env.DEVENV_ROOT}/client";
    LOMAS_CONFIG_PATH = "${lomas_config}";
    LOMAS_SECRETS_PATH = "${lomas_secrets}";
    LOMAS_DASHBOARD_CONFIG_PATH = "${lomas_dashboard}";
    KC_HOME_DIR = "${config.env.DEVENV_STATE}/keycloak";
    KC_CONF_DIR = "${config.env.DEVENV_STATE}/conf";
    KC_BOOTSTRAP_ADMIN_USERNAME = "admin";
    KC_BOOTSTRAP_ADMIN_PASSWORD = "admin";
  };

  packages =
    [
      # required for up pip git+https in containers
      pkgs.git
      pkgs.cacert
      pkgs.openssl
    ]
    # Additional useful packages
    ++ lib.optionals (!config.container.isBuilding) [
      pkgs.jq
      pkgs.yq-go
      pkgs.watchexec
      pkgs.mongosh
      pkgs.kubectl
      pkgs.kubernetes-helm
    ];

  languages.nix.enable = true;

  ##############
  # Python Env #
  ##############

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

  devcontainer.enable = true;
  devcontainer.settings.customizations.vscode.extensions = [
    "mkhl.direnv"
    "jnoortheen.nix-ide"
  ];

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

  processes.rabbitmq.process-compose = {
    readiness_probe = {
      initial_delay_seconds = 10;
      period_seconds = 3;
      timeout_seconds = 3;
      success_threshold = 2;
      failure_threshold = 10;
    };
  };

  ##########
  # WORKER #
  ##########

  processes.worker = {
    exec = ''
      python worker.py
    '';
    process-compose = {
      working_dir = "$DEVENV_ROOT/server/lomas_server";
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
      exec.command = "${lib.getExe pkgs.mongosh} --quiet --eval '{ ping: 1 }' --port ${toString mongo_port} &>/dev/null";
      initial_delay_seconds = 10;
      period_seconds = 3;
      timeout_seconds = 3;
      success_threshold = 2;
      failure_threshold = 10;
    };
  };

  processes.mongodb-configure = import ./devenv/mongo-init.nix {
    inherit
      pkgs
      lib
      mongo_db_name
      mongo_port
      ;
    inherit (config.services.mongodb) initDatabaseUsername initDatabasePassword;
  };

  ############
  # Keycloak #
  ############

  processes.keycloak = import ./devenv/keycloak.nix {
    inherit
      pkgs
      postgres_port
      postgres_addr
      kc_http_port
      kc_https_port
      kc_management_port
      ;
    env = config.env;
    kc_hostname = "localhost";
  };

  # Keycloak requires a postgres
  services.postgres = {
    enable = true;
    port = postgres_port;
    listen_addresses = postgres_addr;
    initialDatabases = [
      {
        name = "keycloak";
        user = "keycloak";
        pass = "${config.env.KC_BOOTSTRAP_ADMIN_PASSWORD}";
      }
    ];
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

  #############
  # GIT HOOKS #
  #############

  git-hooks.hooks = import ./devenv/hooks.nix { env = config.env; };

  enterShell = ''
    echo hello from $GREET
  '';

  #####################
  # Various utilities #
  #####################

  scripts.ut.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    pytest .
    popd
  '';

  scripts.ut-coverage.exec =
    let
      working_dir = "$DEVENV_ROOT/server/lomas_server";
      pc-config-patch = pkgs.writeText "pc-coverage-disable-worker.yaml" (toYAML {
        processes = {
          # patch/override worker definition to force 1 instance and run coverage on it
          worker = {
            inherit working_dir;
            replicas = 1;
            command = "coverage run --source=. -p worker.py";
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
    python -m pdb uvicorn_server.py
    popd
  '';

  scripts.run-worker-debug.exec = ''
    process-compose process stop -v worker-0 worker-1
    pushd $DEVENV_ROOT/server/lomas_server
    python -m pdb worker.py
    popd
  '';

  scripts.run-lomas-dev.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    python uvicorn_server.py &
    ${config.scripts.run-worker-debug.exec}
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
