{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

let
  inherit (import ./devenv/utils.nix lib) wrapScript listToPydanticEnvVar;

  toYAML = lib.generators.toYAML { };
  toPydanticSetting = lib.generators.toJSON { }; # Pydantic-settings decode (env) values as JSON-string
  writeYAML = filename: attrset: pkgs.writeText filename (toYAML attrset);

  # Keycloak
  kc_auth_realm = "master";
  kc_admin_client_id = "admin-cli";

  # Demo data (relative to ./server/lomas_server since we run all scripts from there)
  admin_path_prefix = "${config.devenv.root}/server/data/";
  user_yaml_path = "/collections/user_collection.yaml";
  dataset_yaml_path = "/collections/dataset_collection_devenv.yaml";
in
{
  # import our modules
  imports = [
    ./devenv/lomas.nix
    ./devenv/rabbitmq.nix
    ./devenv/keycloak.nix
    ./devenv/minio.nix
    ./devenv/telemetry.nix
    ./devenv/hooks.nix
    ./devenv/docker-env.nix
    ./devenv/caddy.nix
    ./devenv/dex.nix
  ];

  lomas = {
    enable = true;
    host = "localhost";
    port = 48080;
    baseUrl = "/api";
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
    client.jupyter = {
      port = 8888;
      password = null; # "dprocks";
    };
  };

  lomas.rabbitmq = {
    enable = true;
    host = "localhost";
    port = 5672;
    nodeName = "rabbit@localhost";
    # spin the management interface http://localhost:15672 guest/guest
    user = "guest";
    password = "guest";
    heartbeat = 1800; # Extra super duper long hearbeat timeout for long running tasks in workersss
  };

  lomas.keycloak = {
    enable = true;
    host = "localhost";
    httpPort = 4442;
    httpsPort = 4443;
    httpManagementPort = 4441;
    bootstrapAdminUser = "admin";
    bootstrapAdminPass = "admin";
  };

  lomas.dex = {
    enable = true;
    host = "localhost";
    address = "127.0.0.1";
    port = 4445;
    adminAddress = "127.0.0.1";
    adminPort = 4446;
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

  # No reverse proxy-ing by default
  # TODO needs update if needed
  lomas.caddy.enable = false;

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
    };
  };

  lomas.hooks = {
    enable = true;
    projectConfigFile = "${config.env.DEVENV_ROOT}/pyproject.toml";
  };

  dockerEnv.enable = true;

  process.managers.process-compose.settings.environment = [ "TTY_COMPATIBLE=1" ];

  # Environment variable available inside devenv
  env = {
    GREET = "Lomas env";

    # Ensure `coverage` uses our project config
    COVERAGE_RCFILE = config.lomas.hooks.projectConfigFile;

    # Pydantic note:
    # Even when using a dotenv file, pydantic will still read environment variables as well as the dotenv file, environment variables will always take priority over values loaded from a dotenv file.

    # Lomas Server Runtime
    LOMAS_SERVICE_server__host_ip = config.lomas.host;
    LOMAS_SERVICE_server__host_port = config.lomas.port;
    LOMAS_SERVICE_server__log_level = "info";
    LOMAS_SERVICE_server__reload = "true";
    LOMAS_SERVICE_server__root_path = config.lomas.baseUrl;
    LOMAS_SERVICE_server__submit_limit = 300;
    LOMAS_SERVICE_server__time_attack__method = "jitter";
    LOMAS_SERVICE_server__time_attack__magnitude = 1;

    LOMAS_SERVICE_amqp__url = "amqp://${config.lomas.rabbitmq.host}:${toString config.lomas.rabbitmq.port}";
    LOMAS_SERVICE_amqp__username = config.lomas.rabbitmq.user;
    LOMAS_SERVICE_amqp__password = config.lomas.rabbitmq.password;
    LOMAS_SERVICE_amqp__heartbeat = config.lomas.rabbitmq.heartbeat;
    LOMAS_SERVICE_opendp_features = toPydanticSetting [
      "contrib"
      "floating-point"
      "honest-but-curious"
    ];
    LOMAS_SERVICE_admin_database_url = "/tmp/admin.db";
    LOMAS_SERVICE_authenticator__authentication_type = "jwt";
    LOMAS_SERVICE_authenticator__keycloak_url = "http://localhost:${toString config.lomas.keycloak.httpPort}";
    LOMAS_SERVICE_authenticator__realm = config.lomas.realm;

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
    LOMAS_GATEWAY_URL = "http://localhost:8080";
    LOMAS_KC_SETUP_KEYCLOAK_URL = "http://${config.lomas.keycloak.host}:${toString config.lomas.keycloak.httpPort}";
    LOMAS_KC_SETUP_KEYCLOAK_AUTHENTICATION_REALM = kc_auth_realm;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_CLIENT_ID = kc_admin_client_id;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_USER = config.lomas.keycloak.bootstrapAdminUser;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_PWD = config.lomas.keycloak.bootstrapAdminPass;
    LOMAS_KC_SETUP_LOMAS_REALM = config.lomas.realm;
    LOMAS_KC_SETUP_LOMAS_GATEWAY_URL = "${config.env.LOMAS_GATEWAY_URL}/auth";
    LOMAS_KC_SETUP_LOMAS_GATEWAY_CLIENT_ID = "lomas-oauth-proxy";
    LOMAS_KC_SETUP_LOMAS_GATEWAY_CLIENT_SECRET = "lomas-oauth-proxy";
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_ID = config.lomas.admin.client_id;
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_SECRET = config.lomas.admin.client_secret;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_ID = config.lomas.api.client_id;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_SECRET = config.lomas.api.client_secret;
    LOMAS_KC_SETUP_OVERWRITE_REALM = "true";

    # Lomas demo setup
    LOMAS_ADMIN_server_url = "http://localhost:${toString config.lomas.port}"; # public lomas service url from dashboard
    LOMAS_ADMIN_server_service = "http://localhost:${toString config.lomas.port}";
    LOMAS_ADMIN_database_url = "/tmp/admin.db";
    LOMAS_ADMIN_KC_CONFIG__URL = "http://${config.lomas.keycloak.host}:${toString config.lomas.keycloak.httpPort}";
    LOMAS_ADMIN_KC_CONFIG__REALM = config.lomas.realm;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_ID = config.lomas.admin.client_id;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_SECRET = config.lomas.admin.client_secret;
    LOMAS_ADMIN_PATH_PREFIX = admin_path_prefix;
    LOMAS_ADMIN_USER_YAML = user_yaml_path;
    LOMAS_ADMIN_DATASET_YAML = dataset_yaml_path;
  }
  // (listToPydanticEnvVar "LOMAS_SERVICE_private_db_credentials" [
    {
      credentials_name = "minio";
      db_type = "S3_DB";
      access_key_id = config.lomas.minio.rootUser;
      secret_access_key = config.lomas.minio.rootPassword;
    }
  ])
  // (listToPydanticEnvVar "LOMAS_KC_SETUP_LOMAS_ADMIN_USERS" [
    {
      username = "admin";
      email = "admin@example.com";
      temp_password = "admin";
      first_name = "admin";
      last_name = "ofAllAdmins";
    }
  ]);

  cachix.pull = [ "lomas" ];

  packages = [
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

  scripts.pip-fix = wrapScript {
    exec = ''
      uv pip compile pyproject.toml --annotation-style line --all-extras $@ | ${pkgs.gnused}/bin/sed -re '/^-e file:/d' > requirements.txt
    '';
  };

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

  #####################
  # Various utilities #
  #####################

  scripts.ut = wrapScript {
    exec = "pytest -c pyproject.toml .";
  };

  scripts.ut-coverage.exec =
    let
      working_dir = config.env.DEVENV_ROOT;
      pc-config-patch = writeYAML "pc-coverage-disable-worker.yaml" {
        processes = {
          # patch/override worker definition to force 1 instance and run coverage on it
          worker = {
            inherit working_dir;
            replicas = 1;
            command = "coverage run --data-file=.coverage.worker -m lomas_server.worker";
            log_location = "$DEVENV_ROOT/logs/worker.log";
          };
          keycloak-setup = {
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
              minio.condition = "process_healthy";
              keycloak.condition = "process_healthy";
              rabbitmq.condition = "process_healthy";
              keycloak-setup.condition = "process_completed_successfully";
              lomas-server.condition = "process_healthy";
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

      popd > /dev/null
      exit $pytest_return
    '';

  # TODO Check this is enough and does not need to run the tools independently in every
  scripts.run-linter = wrapScript {
    exec = ''
      path=''${@:-.}
      [[ "$path" = "." ]] || echo "linting: $path"
      echo -n 🌑; ruff format "$path"
      echo -n ⚡️; ruff check --fix "$path"
      echo -n 🔧; pydocstringformatter "$path"
      echo -n 🐍; mypy "$path"
    '';
  };

  scripts.build-docs = wrapScript {
    pwd = "docs";
    exec = "python build_docs.py";
  };

  scripts.build-docs-local = wrapScript {
    pwd = "docs";
    exec = ''
      python build_docs.py -l
      xdg-open build/html/index.html
    '';
  };

  scripts.run-notebooks = wrapScript {
    exec = "python -m lomas_client.scripts.run_notebook -a -s -d";
  };

  scripts.run-fastapi = wrapScript {
    pwd = "server/lomas_server";
    exec = "python -m pdb uvicorn_serve.py";
  };

  scripts.run-worker-debug = wrapScript {
    exec = ''
      process-compose process stop -v worker-0 worker-1
      python -m pdb -m lomas_server.worker
    '';
  };

  scripts.run-lomas-dev = wrapScript {
    pwd = "server/lomas_server";
    exec = ''
      python uvicorn_server.py &
      ${config.scripts.run-worker-debug.exec}
    '';
  };

  scripts.docker-compose-up = wrapScript {
    pwd = "server";
    exec = "docker compose --env-file configs/.env.docker-compose up";
  };

  scripts.docker-compose-test = wrapScript {
    pwd = "server";
    exec = ''
      docker compose -f docker-compose.yml --env-file configs/.env.docker-compose run --rm lomas_client python -m lomas_client.scripts.run_notebook --notebook /code/client/notebooks/s3_example_notebook.ipynb
      docker compose -f docker-compose.yml --env-file configs/.env.docker-compose down
    '';
  };

  scripts.docker-compose-down = wrapScript {
    pwd = "server";
    exec = "docker compose --env-file configs/.env.docker-compose down";
  };

  scripts.py-build = wrapScript {
    exec = ''
      uv build --sdist core
      uv build --sdist client
      uv build --sdist server
    '';
  };

  scripts.demo-setup = wrapScript {
    pwd = "server/lomas_server";
    exec = "lomas-demo-setup";
  };

  scripts.restart-lomas = wrapScript {
    exec = ''
      process-compose process restart lomas-server
      process-compose process restart worker-0
      process-compose process restart worker-1
    '';
  };

  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
    ${config.scripts.ut.exec}
  '';

  scripts.yelp.exec = ''
    b=$(tput bold)
    n=$(tput sgr0)
    cat << EOF
    $b- Starting up the environment$n
    devenv up

    $b- Starting up the environment *with telemetry*$n
    process-compose up
    or
    devenv up -- --namespace=telemetry

    $b- What the hell is process-compose doing$n
    yq \$PC_CONFIG_FILES

    $b- I just want my UTs / pytest to work !$n
    devenv up
    ut / pytest -k ...

    $b- Trick: seeing my prints whilst pytesting:$n
    pytest -s / pytest -rA

    optionally --log-cli-level=DEBUG to get spammed again !

    $b- Just run the coverage alreaaady$n
    ut-coverage

    $b- My python packages are broken/out of sync/missing$n
    uv sync --all-extras [-U]
    uv add <packages>
    EOF
  '';
}
