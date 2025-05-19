{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

let
  toYAML = lib.generators.toYAML { };
  toPydanticSetting = lib.generators.toJSON { }; # Pydantic-settings decode (env) values as JSON-string
  writeYAML = filename: attrset: pkgs.writeText filename (toYAML attrset);

  # Keycloak
  kc_auth_realm = "master";
  kc_admin_client_id = "admin-cli";
  kc_setup_overwrite_realm = "true";

  # Jupyter
  jupyter_port = 8888;
  jupyter_pwd = "dprocks";

  # Demo data (relative to ./server/lomas_server since we run all scripts from there)
  admin_path_prefix = "${config.devenv.root}/server/data/";
  user_yaml_path = "/collections/user_collection.yaml";
  dataset_yaml_path = "/collections/dataset_collection_devenv.yaml";
in
{
  # overlay our packages (pkgs) set
  overlays = import ./devenv/overlays.nix;

  # import our modules
  imports = [
    ./devenv/lomas.nix
    ./devenv/hooks.nix
    ./devenv/rabbit.nix
    ./devenv/minio.nix
    ./devenv/keycloak.nix
    ./devenv/mongodb.nix
    ./devenv/telemetry.nix
  ];

  lomas = {
    enable = true;
    host = "localhost";
    port = 48080;
    dashboard.host = "localhost";
    dashboard.port = 8501;
    admin = {
      client_id = "lomas_admin";
      client_secret = "lomas_admin";
    };
    api = {
      client_id = "lomas_api";
      client_secret = "lomas_api";
    };
  };

  lomas.hooks = {
    enable = true;
    projectConfigFile = "${config.env.DEVENV_ROOT}/pyproject.toml";
  };

  lomas.rabbitmq = {
    enable = true;
    host = "localhost";
    port = 5672;
    nodeName = "rabbit@localhost";
    # spin the management interface http://localhost:15672 guest/guest
    portManagement = 15672;
    user = "guest";
    password = "guest";
    heartbeat = 1800; # Extra super duper long hearbeat timeout for long running tasks in workersss
  };

  lomas.minio = {
    enable = true;
    host = "localhost";
    port = 19000;
    console_port = 19001;
    rootUser = "admin";
    rootPassword = "admin123";
    initFilesCopy = [
      {
        src = ./server/lomas_server/tests/test_data/test_penguin.csv;
        dst = "/data/test_penguin.csv";
      }
      {
        src = ./server/lomas_server/tests/test_data/metadata/penguin_metadata.yaml;
        dst = "/metadata/penguin_metadata.yaml";
      }
      {
        src = ./server/data/datasets/titanic.csv;
        dst = "/data/titanic.csv";
      }
      {
        src = ./server/data/collections/metadata/titanic_metadata.yaml;
        dst = "/metadata/titanic_metadata.yaml";
      }
    ];
  };

  lomas.keycloak = {
    enable = true;
    host = "localhost";
    httpPort = 4442;
    httpsPort = 4443;
    httpManagementPort = 4441;
    bootstrapAdminUser = "admin";
    bootstrapAdminPass = "admin";
    postgres_addr = "localhost";
    postgres_port = 5432;
  };

  lomas.mongo = {
    enable = true;
    host = "localhost";
    port = 27017;
    dbName = "defaultdb";
    extraDbNames = [ "testdb" ];
    initialUser = "root";
    initialPassword = "root_pwd";
    user = "user";
    password = "password";
  };

  lomas.telemetry = {
    enable = true;
    namespace = "telemetry";
    services = {
      grafana = {
        host = "localhost";
        port = 3000;
      };
      prometheus = {
        host = "localhost";
        port = 19090;
      };
      tempo = {
        host = "localhost";
        ports = {
          http = 13200;
          grpc = 19095;
          otlp_grpc = 14317;
        };
      };
      loki = {
        host = "localhost";
        port = 13100;
      };
      otlp = {
        host = "localhost";
        ports = {
          grpc = 4317; # Must keep this value
          http = 4318; # Must keep this value
          metrics = 29090;
        };
      };
      mongodbExporter = {
        host = "localhost";
        port = 9216;
      };
    };
  };

  # Environment variable available inside devenv
  env = {
    GREET = "Lomas env";

    # Ensure `coverage` uses our project config
    COVERAGE_RCFILE = "${config.env.DEVENV_ROOT}/pyproject.toml";

    # Pydantic note:
    # Even when using a dotenv file, pydantic will still read environment variables as well as the dotenv file, environment variables will always take priority over values loaded from a dotenv file.

    # Lomas Server Runtime
    LOMAS_SERVICE_server__host_ip = "0.0.0.0";
    LOMAS_SERVICE_server__host_port = config.lomas.port;
    LOMAS_SERVICE_server__log_level = "info";
    LOMAS_SERVICE_server__reload = "true";
    LOMAS_SERVICE_server__submit_limit = 300;
    LOMAS_SERVICE_server__time_attack__method = "jitter";
    LOMAS_SERVICE_server__time_attack__magnitude = 1;

    LOMAS_SERVICE_amqp__url = "amqp://${config.lomas.rabbitmq.host}:${toString config.lomas.rabbitmq.port}";
    LOMAS_SERVICE_amqp__username = config.lomas.rabbitmq.user;
    LOMAS_SERVICE_amqp__password = config.lomas.rabbitmq.password;
    LOMAS_SERVICE_opendp_features = toPydanticSetting [
      "contrib"
      "floating-point"
      "honest-but-curious"
    ];
    LOMAS_SERVICE_admin_database__url = config.lomas.mongo.dsn;
    LOMAS_SERVICE_admin_database__username = config.lomas.mongo.user;
    LOMAS_SERVICE_admin_database__password = config.lomas.mongo.password;
    LOMAS_SERVICE_admin_database__max_pool_size = config.lomas.mongo.maxPoolSize;
    LOMAS_SERVICE_admin_database__min_pool_size = config.lomas.mongo.minPoolSize;
    LOMAS_SERVICE_admin_database__max_connecting = config.lomas.mongo.maxConnecting;
    LOMAS_SERVICE_authenticator__authentication_type = "jwt";
    LOMAS_SERVICE_authenticator__keycloak_url = "http://localhost:${toString config.lomas.keycloak.httpPort}";
    LOMAS_SERVICE_authenticator__realm = config.lomas.realm;
    LOMAS_SERVICE_private_db_credentials__0__credentials_name = "minio";
    LOMAS_SERVICE_private_db_credentials__0__db_type = "S3_DB";
    LOMAS_SERVICE_private_db_credentials__0__access_key_id = config.lomas.minio.rootUser;
    LOMAS_SERVICE_private_db_credentials__0__secret_access_key = config.lomas.minio.rootPassword;

    LOMAS_SERVICE_telemetry__enabled = "false";
    LOMAS_SERVICE_telemetry__service_name = "lomas-server-app";
    LOMAS_SERVICE_telemetry__service_id = "default-host";
    LOMAS_SERVICE_telemetry__collector_endpoint = "http://localhost:${toString config.lomas.telemetry.services.otlp.ports.grpc}";
    LOMAS_SERVICE_telemetry__collector_insecure = "true";

    # Lomas client environment
    LOMAS_CLIENT_KEYCLOAK_URL = "http://${config.lomas.keycloak.host}:${toString config.lomas.keycloak.httpPort}";
    LOMAS_CLIENT_REALM = config.lomas.realm;
    LOMAS_CLIENT_APP_URL = "http://localhost:${toString config.lomas.port}";

    LOMAS_CLIENT_telemetry__enabled = "false";
    LOMAS_CLIENT_telemetry__service_name = "lomas-server-app";
    LOMAS_CLIENT_telemetry__service_id = "default-host";
    LOMAS_CLIENT_telemetry__collector_endpoint = "http://localhost:${toString config.lomas.telemetry.services.otlp.ports.grpc}";
    LOMAS_CLIENT_telemetry__collector_insecure = "true";

    # Keycloak setup
    LOMAS_KC_SETUP_KEYCLOAK_URL = "http://${config.lomas.keycloak.host}:${toString config.lomas.keycloak.httpPort}";
    LOMAS_KC_SETUP_KEYCLOAK_AUTHENTICATION_REALM = kc_auth_realm;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_CLIENT_ID = kc_admin_client_id;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_USER = config.lomas.keycloak.bootstrapAdminUser;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_PWD = config.lomas.keycloak.bootstrapAdminPass;
    LOMAS_KC_SETUP_LOMAS_REALM = config.lomas.realm;
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_ID = config.lomas.admin.client_id;
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_SECRET = config.lomas.admin.client_secret;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_ID = config.lomas.api.client_id;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_SECRET = config.lomas.api.client_secret;
    LOMAS_KC_SETUP_OVERWRITE_REALM = kc_setup_overwrite_realm;

    # Lomas demo setup
    LOMAS_ADMIN_server_url = "http://localhost:${toString config.lomas.port}"; # public lomas service url from dashboard
    LOMAS_ADMIN_server_service = "http://localhost:${toString config.lomas.port}";
    LOMAS_ADMIN_MG_CONFIG__url = config.lomas.mongo.dsn;
    LOMAS_ADMIN_MG_CONFIG__username = config.lomas.mongo.user;
    LOMAS_ADMIN_MG_CONFIG__password = config.lomas.mongo.password;
    LOMAS_ADMIN_KC_CONFIG__URL = "http://${config.lomas.keycloak.host}:${toString config.lomas.keycloak.httpPort}";
    LOMAS_ADMIN_KC_CONFIG__REALM = config.lomas.realm;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_ID = config.lomas.admin.client_id;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_SECRET = config.lomas.admin.client_secret;
    LOMAS_ADMIN_PATH_PREFIX = admin_path_prefix;
    LOMAS_ADMIN_USER_YAML = user_yaml_path;
    LOMAS_ADMIN_DATASET_YAML = dataset_yaml_path;
  };

  cachix.pull = [ "lomas" ];

  packages =
    [
      # required for up pip git+https in containers
      pkgs.git
      pkgs.cacert
    ]
    # Additional useful packages
    ++ lib.optionals (!config.container.isBuilding) [
      pkgs.jq
      pkgs.yq-go
      pkgs.watchexec
      pkgs.kubectl
      pkgs.kubernetes-helm
    ];

  languages.nix.enable = !config.container.isBuilding;

  ##############
  # Python Env #
  ##############

  scripts.pip-fix.exec = ''
    pushd $DEVENV_ROOT
    uv pip compile pyproject.toml --annotation-style line --all-extras $@ | ${pkgs.gnused}/bin/sed -re '/^-e file:/d' > requirements.txt
    popd
  '';

  languages.python = {
    enable = true;
    venv.enable = true;
    uv.enable = true;
  };

  devcontainer = {
    enable = true;
    settings.customizations.vscode.extensions = [
      "mkhl.direnv"
      "jnoortheen.nix-ide"
    ];
  };

  ##########
  # WORKER #
  ##########

  processes.worker = {
    exec = "python worker.py";
    process-compose = {
      working_dir = "$DEVENV_ROOT/server/lomas_server";
      depends_on.rabbitmq.condition = "process_healthy";
      replicas = 2;
      # Un-comment to observe worker logs.
      # log_location = "$DEVENV_ROOT/logs/worker.log";
    };
  };

  enterShell = ''
    echo hello from $GREET

    UV_SYNC_COMMAND=(uv sync --frozen --all-extras)

    # Avoid running "uv sync" for every shell. Only run it when the "pyproject.toml" file or Python interpreter has changed.
    [[ -f "$UV_PROJECT_ENVIRONMENT/.devenv_interpreter" ]] && read -r PYTHON_INTERPRETER < "$UV_PROJECT_ENVIRONMENT/.devenv_interpreter" || PYTHON_INTERPRETER=""

    ACTUAL_UV_CHECKSUM="''${PYTHON_INTERPRETER}:$(${pkgs.nix}/bin/nix-hash --type sha256 pyproject.toml):''${UV_SYNC_COMMAND[@]}"
    UV_CHECKSUM_FILE="$UV_PROJECT_ENVIRONMENT/uv.sync.checksum"

    [[ -f "$UV_CHECKSUM_FILE" ]] && read -r EXPECTED_UV_CHECKSUM < "$UV_CHECKSUM_FILE" || EXPECTED_UV_CHECKSUM=""

    if [ "$ACTUAL_UV_CHECKSUM" != "$EXPECTED_UV_CHECKSUM" ]; then
      if "''${UV_SYNC_COMMAND[@]}"; then
        echo "$ACTUAL_UV_CHECKSUM" > "$UV_CHECKSUM_FILE"
      else
        echo "uv sync failed. Run 'uv sync' manually." >&2
        exit 1
      fi
    fi
  '';

  #########
  # Tasks #
  #########

  tasks = {
    # Create .env file for those who want to use docker compose.
    "filegen:env_docker_compose" = {
      before = [ "devenv:enterShell" ];
      exec = ''
        cat > $DEVENV_ROOT/server/configs/.env.docker-compose <<EOF
        # This file was autogenerated by devenv

        # Lomas service
        LOMAS_SERVICE_PORT=${toString config.lomas.port}

        # Keycloak
        LOMAS_KC_PORT=${toString config.lomas.keycloak.httpPort}
        LOMAS_KC_ADMIN_USER=${config.lomas.keycloak.bootstrapAdminUser}
        LOMAS_KC_ADMIN_PWD=${config.lomas.keycloak.bootstrapAdminPass}

        # RabbitMQ
        LOMAS_RABBIT_MQ_PORT=${toString config.lomas.rabbitmq.port}
        LOMAS_RABBIT_MQ_MGMT_PORT=${toString config.lomas.rabbitmq.portManagement}
        LOMAS_RABBIT_MQ_USER=${config.lomas.rabbitmq.user}
        LOMAS_RABBIT_MQ_PASS=${config.lomas.rabbitmq.password}

        # MongoDB
        LOMAS_MONGO_PORT=${toString config.lomas.mongo.port}
        LOMAS_MONGO_ROOT_USER=${config.lomas.mongo.initialUser}
        LOMAS_MONGO_ROOT_PWD=${config.lomas.mongo.initialPassword}
        LOMAS_MONGO_DATABASE=${config.lomas.mongo.dbName}

        # Dashboard
        LOMAS_DASHBOARD_PORT=${toString config.lomas.dashboard.port}

        # MinIO
        LOMAS_MINIO_PORT=${toString config.lomas.minio.port}
        LOMAS_MINIO_CONSOLE_PORT=${toString config.lomas.minio.console_port}
        LOMAS_MINIO_ROOT_USER=${config.lomas.minio.rootUser}
        LOMAS_MINIO_ROOT_PWD=${config.lomas.minio.rootPassword}

        # Telemetry
        LOMAS_OTEL_PORT=${toString config.lomas.telemetry.services.otlp.ports.grpc}
        LOMAS_MONGO_COLLECTOR_PORT=${toString config.lomas.telemetry.services.mongodbExporter.port}

        # Client
        LOMAS_CLIENT_PORT=${toString jupyter_port}
        EOF
      '';
    };

    "filegen:env_docker_compose_service" =
      let
        kcEnvVar = lib.filterAttrs (name: value: lib.strings.hasPrefix "LOMAS_SERVICE_" name) config.env;
        kcEnvVarFinal = kcEnvVar // {
          LOMAS_SERVICE_amqp__url = "amqp://rabbitmq:${toString config.lomas.rabbitmq.port}";
          LOMAS_SERVICE_authenticator__keycloak_url = "http://keycloak:${toString config.lomas.keycloak.httpPort}";
          LOMAS_SERVICE_admin_database__url = "mongodb://mongodb:${toString config.lomas.mongo.port}/${config.lomas.mongo.dbName}";
          LOMAS_SERVICE_telemetry__collector_endpoint = "http://otel-collector:${toString config.lomas.telemetry.services.otlp.ports.grpc}";
        };
      in
      {
        before = [ "devenv:enterShell" ];
        exec = ''
          cat > $DEVENV_ROOT/server/configs/.env.lomas_service <<EOF
          # This file was autogenerated by devenv
          ${lib.generators.toKeyValue { } kcEnvVarFinal}
          EOF
        '';
      };

    "filegen:env_docker_compose_client" =
      let
        kcEnvVar = lib.filterAttrs (name: value: lib.strings.hasPrefix "LOMAS_CLIENT_" name) config.env;
        kcEnvVarFinal = kcEnvVar // {
          LOMAS_CLIENT_APP_URL = "http://lomas_server:${toString config.lomas.port}";
          LOMAS_CLIENT_KEYCLOAK_URL = "http://keycloak:${toString config.lomas.keycloak.httpPort}";
          LOMAS_CLIENT_telemetry__collector_endpoint = "http://otel-collector:${toString config.lomas.telemetry.services.otlp.ports.grpc}";
        };
      in
      {
        before = [ "devenv:enterShell" ];
        exec = ''
          cat > $DEVENV_ROOT/server/configs/.env.lomas_client <<EOF
          # This file was autogenerated by devenv
          ${lib.generators.toKeyValue { } kcEnvVarFinal}
          EOF
        '';
      };

    "filegen:env_docker_compose_kc_setup" =
      let
        kcEnvVar = lib.filterAttrs (name: value: lib.strings.hasPrefix "LOMAS_KC_" name) config.env;
        kcEnvVarFinal = kcEnvVar // {
          LOMAS_KC_SETUP_KEYCLOAK_URL = "http://keycloak:${toString config.lomas.keycloak.httpPort}";
        };
      in
      {
        before = [ "devenv:enterShell" ];
        exec = ''
          cat > $DEVENV_ROOT/server/configs/administration/.env.keycloak_setup <<EOF
          # This file was autogenerated by devenv
          ${lib.generators.toKeyValue { } kcEnvVarFinal}
          EOF
        '';
      };

    "filegen:env_docker_compose_admin" =
      let
        adminVar = lib.filterAttrs (name: value: lib.strings.hasPrefix "LOMAS_ADMIN_" name) config.env;
        adminVarFinal = adminVar // {
          LOMAS_ADMIN_KC_CONFIG__URL = "http://keycloak:${toString config.lomas.keycloak.httpPort}";
          LOMAS_ADMIN_MG_CONFIG__URL = "mongodb://mongodb:${toString config.lomas.mongo.port}/${config.lomas.mongo.dbName}";
          LOMAS_ADMIN_DATASET_YAML = "/collections/dataset_collection.yaml";
          LOMAS_ADMIN_PATH_PREFIX = "/data";
        };
      in
      {
        before = [ "devenv:enterShell" ];
        exec = ''
          cat > $DEVENV_ROOT/server/configs/administration/.env.lomas_demo_setup <<EOF
          # This file was autogenerated by devenv
          ${lib.generators.toKeyValue { } adminVarFinal}
          EOF
        '';
      };

    "filegen:mongo_init" = {
      before = [ "devenv:enterShell" ];
      exec = ''
        cat > $DEVENV_ROOT/server/configs/mongodb_init.js <<EOF
        // This file was autogenerated by devenv.
        db.createUser({
          user: "${config.lomas.mongo.user}",
          pwd: "${config.lomas.mongo.password}",
          roles: [{ role: "readWrite", db: "${config.lomas.mongo.dbName}" }]}
        );
        EOF
      '';
    };

    "filegen:jupyter_config" = {
      before = [ "devenv:enterShell" ];
      exec = ''
        cat > $DEVENV_ROOT/client/configs/jupyter_notebook_config.py <<EOF
        # type: ignore
        # This file was autogenerated by devenv.
        from jupyter_server.auth import passwd

        c = get_config()  # noqa: F821
        password: str = "${jupyter_pwd}"
        c.NotebookApp.password = passwd(password)
        c.NotebookApp.port = ${toString jupyter_port}
        EOF
      '';
    };
  };

  #####################
  # Various utilities #
  #####################

  scripts.ut.exec = ''
    pushd $DEVENV_ROOT/
    pytest -c $DEVENV_ROOT/pyproject.toml .
    popd
  '';

  scripts.ut-coverage.exec =
    let
      working_dir = "$DEVENV_ROOT";
      pc-config-patch = writeYAML "pc-coverage-disable-worker.yaml" {
        processes = {
          # patch/override worker definition to force 1 instance and run coverage on it
          worker = {
            inherit working_dir;
            replicas = 1;
            command = "coverage run --data-file=.coverage.worker -m lomas_server.worker";
            log_location = "$DEVENV_ROOT/logs/worker.log";
          };
          keycloak_setup = {
            inherit working_dir;
            command = "coverage run --data-file=.coverage.keycloak_setup server/lomas_server/administration/scripts/keycloak_setup.py";
          };
          # Add this ad-hoc pytest process to be run in foreground whilst ensuring
          # all background dependencies
          pytest-cov = {
            inherit working_dir;
            command = "pytest --cov-append --cov-report term-missing --cov --no-cov-on-fail --cov-config=${config.env.COVERAGE_RCFILE} \"$@\"";
            depends_on = {
              worker.condition = "process_started";
              minio.condition = "process_ready";
              mongodb.condition = "process_ready";
              mongodb-configure.condition = "process_completed_successfully";
              keycloak.condition = "process_ready";
              rabbitmq.condition = "process_ready";
              keycloak_setup.condition = "process_completed_successfully";
              lomas-server.condition = "process_ready";
            };
            log_location = "$DEVENV_ROOT/logs/pytest.log";
            log_configuration.flush_each_line = true;
            # We terminate the whole process-compose at the end of this task
            availability.exit_on_end = true;
          };
        };
      };
    in
    ''
      # if any arguments given: consume first as root path (zb. server/) and forward the rest to pytest (zb. -v / -x / -k ...)
      path=''${1:-.}
      [[ $# > 0 ]] && shift
      pushd ${working_dir}
      echo "Running coverage on $path with patched process-compose config (${pc-config-patch})"
      yq -Poy ${pc-config-patch}
      process-compose run pytest-cov -f $PC_CONFIG_FILES -f ${pc-config-patch} -- "$path" "$@"
      pytest_return=$?

      if [ $pytest_return -eq 0 ]; then
        echo "✅ test success -> building coverage"
        # these per-process coverages are generated by coverage run -p <...>
        coverage combine -a .coverage.*
      fi

      popd
      exit $pytest_return
    '';

  # TODO Check this is enough and does not need to run the tools independently in every
  scripts.run-linter.exec = ''
    pushd $DEVENV_ROOT
    path=''${@:-.}
    [[ "$path" = "." ]] || echo "linting: $path"
    echo -n 🌑; black "$path"
    echo -n ⚡️; ruff check --fix "$path"
    echo -n 🐌; pylint "$path"
    echo -n 🔧; pydocstringformatter "$path"
    echo -n 🐍; mypy "$path"
    popd
  '';

  scripts.run-notebooks.exec = ''
    pushd $DEVENV_ROOT
    python -m lomas_client.scripts.run_notebook -a -s -d
    popd
  '';

  scripts.run-jupyter.exec = ''
    pushd $DEVENV_ROOT/client
    jupyter notebook --ip 0.0.0.0 --port ${toString jupyter_port} --no-browser --allow-root
    popd
  '';

  scripts.run-fastapi.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    python -m pdb uvicorn_serve.py
    popd
  '';

  scripts.run-worker-debug.exec = ''
    process-compose process stop -v worker-0 worker-1
    pushd $DEVENV_ROOT
    python -m pdb lomas_server.worker
    popd
  '';

  scripts.run-lomas-dev.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    python uvicorn_server.py &
    ${config.scripts.run-worker-debug.exec}
    popd
  '';

  scripts.docker-compose-up.exec = ''
    pushd $DEVENV_ROOT/server/
    docker compose --env-file configs/.env.docker-compose up
    popd
  '';

  scripts.docker-compose-test.exec = ''
    pushd $DEVENV_ROOT/server/
    docker compose -f docker-compose.yml --env-file configs/.env.docker-compose run --rm lomas_client python -m lomas_client.scripts.run_notebook --notebook /code/client/notebooks/s3_example_notebook.ipynb
    docker compose -f docker-compose.yml --env-file configs/.env.docker-compose down
    popd
  '';

  scripts.docker-compose-down.exec = ''
    pushd $DEVENV_ROOT/server/
    docker compose --env-file configs/.env.docker-compose down
    popd
  '';

  scripts.py-build.exec = ''
    pushd $DEVENV_ROOT
    uv build --sdist core
    uv build --sdist client
    uv build --sdist server
    popd
  '';

  scripts.demo_setup.exec = ''
    pushd $DEVENV_ROOT/server/lomas_server
    lomas-demo-setup
    popd
  '';

  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
    ${config.scripts.ut.exec}
  '';

  scripts.yelp.exec = ''
    cat << EOF
    - Starting up the environment
    devenv up

    - Starting up the environment *with telemetry*
    process-compose up
    or
    devenv up -- --namespace=telemetry

    - What the hell is process-compose doing
    yq \$PC_CONFIG_FILES

    - I just want my UTs / pytest to work !
    devenv up
    ut / pytest -k ...

    - Just run the coverage alreaaady
    ut-coverage

    - My python packages are broken/out of sync/missing
    uv sync --all-extras [-U]
    uv add <packages>
    EOF
  '';
}
