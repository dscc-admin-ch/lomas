{
  pkgs,
  lib,
  config,
  ...
}:

let
  inherit
    (import ./devenv/utils.nix {
      inherit lib;
      inherit (config.git) root;
    })
    wrapScript
    listToPydanticEnvVar
    ;

  toPydanticSetting = lib.generators.toJSON { }; # Pydantic-settings decode (env) values as JSON-string

  # Demo data (relative to ./server/lomas_server since we run all scripts from there)
  admin_data_dir = "${config.git.root}/server/data";
  user_yaml_path = "${admin_data_dir}/collections/user_collection.yaml";
  dataset_yaml_path = "${admin_data_dir}/collections/dataset_collection_devenv.yaml";
in
{
  # import our modules
  imports = [
    ./devenv/lomas.nix
    ./devenv/rabbitmq.nix
    ./devenv/garage.nix
    ./devenv/telemetry.nix
    ./devenv/hooks.nix
    ./devenv/docker-env.nix
    ./devenv/dex.nix
    ./devenv/pyenv.nix
  ];

  lomas = {
    enable = true;
    host = "localhost";
    port = 48080;
    dashboard.host = "localhost";
    dashboard.port = 8501;
    client.jupyter = {
      port = 8888;
      password = null; # "dprocks";
    };
  };

  lomas.oidc = {
    enable = true;
    providerUrl = "http://localhost:4445/dex";
    queryUserinfo = true;
    clients = {
      apiServer = {
        client_id = "lomas_api";
        client_secret = "lomas_api";
      };
      apiClient = "lomas_client";
      adminDashboard = {
        client_id = "lomas_dashboard";
        client_secret = "lomas_dashboard";
        redirect_uri = with config.lomas.dashboard; "http://${host}:${toString port}${baseUrl}/oauth2callback";
      };
      grafanaDashboard = {
        client_id = "lomas_grafana";
        client_secret = "lomas_grafana";
        redirect_uri = with config.lomas.telemetry.services.grafana; "http://${host}:${toString port}/login/generic_oauth";
      };
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

  lomas.dex = {
    enable = true;
    port = 4445;
    host = "localhost";
    address = "127.0.0.1";
    adminPort = 4446;
    adminAddress = "127.0.0.1";
  };

  lomas.garage = {
    enable = true;
    host = "localhost";
    port = 3900;
    rpcPort = 3901;
    apiPort = 3903;
    # GK + 12 hex-encoded bytes
    keyId = "GK0123456789abcdefdeadbeef";
    # 32 hex-encoded bytes
    secretKey = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    initFilesCopy = [
      {
        src = builtins.path {
          name = "penguinData";
          path = ./server/lomas_server/tests/test_data/test_penguin.csv;
        };
        dst = "/data/test_penguin.csv";
      }
      {
        src = builtins.path {
          name = "penguinMetadata";
          path = ./server/lomas_server/tests/test_data/metadata/penguin_metadata.json;
        };
        dst = "/metadata/penguin_metadata.json";
      }
      {
        src = builtins.path {
          name = "Titanic";
          path = ./server/data/datasets/titanic.csv;
        };
        dst = "/data/titanic.csv";
      }
      {
        src = builtins.path {
          name = "TitanicMetadata";
          path = ./server/data/collections/metadata/titanic_metadata.json;
        };
        dst = "/metadata/titanic_metadata.json";
      }
    ];
  };

  lomas.telemetry = {
    enable = lib.mkDefault false;
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
    projectConfigFile = "${config.git.root}/pyproject.toml";
  };

  lomas.pyenv = {
    enable = true;
    package = lib.mkDefault pkgs.python3;
  };

  dockerEnv.enable = true;

  profiles = {
    telemetry.module = {
      lomas.telemetry.enable = true;
    };

    coverage.module = {
      process.manager.implementation = "native";
      processes.worker = {
        cwd = lib.mkForce "${config.git.root}";
        exec = lib.mkForce "mkdir -p ./logs/ && exec coverage run --data-file=.coverage.worker -m lomas_server.worker &> ./logs/worker.log";
      };

      # override the UT script to generate coverage
      scripts.ut = wrapScript {
        exec = ''
          mkdir -p ./logs/ && exec pytest --cov-append --cov-report term-missing --cov --no-cov-on-fail --cov-config=${config.env.COVERAGE_RCFILE} &> ./logs/pytest.log
        '';
      };

    };
  };

  process.manager.implementation = lib.mkDefault "process-compose";
  process.managers.process-compose.settings.environment = [ "TTY_COMPATIBLE=1" ];

  # Environment variable available inside devenv
  env = {
    GREET = "Lomas env";
    NO_MKDOCS_2_WARNING = 1;

    # Ensure `coverage` uses our project config
    COVERAGE_RCFILE = config.lomas.hooks.projectConfigFile;

    # Pydantic note:
    # Even when using a dotenv file, pydantic will still read environment variables as well as the dotenv file, environment variables will always take priority over values loaded from a dotenv file.
    # Too many unrelated (3party dep warnings for now)
    # PYTHONWARNDEFAULTENCODING = 1;

    # Lomas Server Runtime
    LOMAS_SERVICE_server__host_ip = config.lomas.host;
    LOMAS_SERVICE_server__host_port = config.lomas.port;
    LOMAS_SERVICE_server__log_level = "INFO";
    LOMAS_SERVICE_server__lomas_log_level = "DEBUG";
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
      "idealized-numerics"
      "honest-but-curious"
    ];
    LOMAS_SERVICE_database_directory = "/tmp/lomas-db/";
    LOMAS_SERVICE_data_directory = "${config.git.root}/server/data/";
    LOMAS_SERVICE_clean_admin_database = "false";
    LOMAS_SERVICE_bootstrap = "deadbeef";
    LOMAS_SERVICE_authenticator__authentication_type = if config.lomas.oidc.enable then "oidc" else "free_pass";
    LOMAS_SERVICE_authenticator__oidc_discovery_url = "${config.lomas.oidc.discoveryUrl}";
    LOMAS_SERVICE_authenticator__query_userinfo = "${lib.boolToString config.lomas.oidc.queryUserinfo}";

    # Lomas client environment
    LOMAS_CLIENT_OIDC_DISCOVERY_URL = config.lomas.oidc.discoveryUrl;
    LOMAS_CLIENT_USE_PASSWORD_FLOW = "true";
    LOMAS_CLIENT_APP_URL = "http://localhost:${toString config.lomas.port}";

    # Lomas demo setup
    LOMAS_ADMIN_server_url = "http://localhost:${toString config.lomas.port}"; # public lomas service url from dashboard
    LOMAS_ADMIN_server_service = "http://localhost:${toString config.lomas.port}";
    LOMAS_ADMIN_USER_YAML = user_yaml_path;
    LOMAS_ADMIN_DATASET_YAML = dataset_yaml_path;
    LOMAS_ADMIN_DEX_CONFIG__URL = "grpc://${config.lomas.dex.adminAddress}:${toString config.lomas.dex.adminPort}";
    LOMAS_ADMIN_BOOTSTRAP = config.env.LOMAS_SERVICE_bootstrap;
  }
  // (listToPydanticEnvVar "LOMAS_SERVICE_private_db_credentials" [
    {
      credentials_name = "garage";
      db_type = "S3_DB";
      access_key_id = config.lomas.garage.keyId;
      secret_access_key = config.lomas.garage.secretKey;
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
    pkgs.nix-output-monitor
    pkgs.jq
    pkgs.yq-go
    pkgs.watchexec
    pkgs.skopeo
    pkgs.kubectl
    pkgs.kubernetes-helm
  ];

  languages.nix.enable = !config.container.isBuilding;

  ##############
  # Python Env #
  ##############

  languages.python = {
    enable = true;
    venv.enable = !config.lomas.pyenv.enable;
    uv.enable = !config.lomas.pyenv.enable;
  };

  enterShell = ''
    echo hello from $GREET
  ''
  + (lib.optionalString (!config.lomas.pyenv.enable) ''

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
  '');

  #####################
  # Various utilities #
  #####################

  scripts.ut = lib.mkDefault (wrapScript {
    exec = "pytest -c pyproject.toml";
  });

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
    exec = "mkdocs build";
  };

  scripts.build-docs-local = wrapScript {
    exec = ''
      mkdocs serve -o
    '';
  };

  scripts.run-notebooks = wrapScript {
    exec = "python -m lomas_client.scripts.run_notebook -a -s -d";
  };

  scripts.run-fastapi = wrapScript {
    pwd = "server/lomas_server";
    exec = "python -m pdb cli.py start";
  };

  scripts.run-worker-debug = wrapScript {
    exec = ''
      ${pkgs.procps}/bin/pkill -f 'lomas work'
      python -m pdb -m lomas_server.worker
    '';
  };

  scripts.run-lomas-dev = wrapScript {
    pwd = "server/lomas_server";
    exec = ''
      python cli.py start &
      ${config.scripts.run-worker-debug.exec}
    '';
  };

  scripts.docker-compose-up = wrapScript {
    pwd = "server";
    exec = "docker compose --env-file configs/.env.docker-compose up";
  };

  scripts.docker-load-image = wrapScript {
    exec = ''
      echo "building lomas OCI"
      nix build ''${DEVENV_ROOT:=.}#lomas-oci -o oci_archive
      echo "loading into docker"
      TMPDIR=/tmp docker load -i oci_archive
    '';
  };

  scripts.docker-compose-test = wrapScript {
    pwd = "server";
    exec = ''
      docker compose -f docker-compose.yml --env-file configs/.env.docker-compose run --rm lomas_client python -m lomas_client.scripts.run_notebook --notebook /code/client/notebooks/Demo_Client_Notebook_OpenDP_Polars_features.ipynb
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

  scripts.collectCoverage = wrapScript {
    exec = "coverage combine -a .coverage.*";
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
    devenv -P telemetry up

    $b- I just want my UTs / pytest to work !$n
    devenv up
    ut / pytest -k ...

    $b- Trick: seeing my prints whilst pytesting:$n
    pytest -s / pytest -rA

    optionally --log-cli-level=DEBUG to get spammed again !

    $b- Just run the coverage alreaaady$n
    devenv -P coverage test

    $b- My python packages are broken/out of sync/missing$n
    uv sync --all-extras [-U]
    uv add <packages>
    EOF
  '';
}
