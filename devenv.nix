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
    ./modules/_defaults.nix
    ./devenv/lomas.nix
    ./devenv/garage.nix
    ./devenv/telemetry.nix
    ./devenv/hooks.nix
    ./devenv/docker-env.nix
    ./devenv/dex.nix
    ./devenv/pyenv.nix
  ];

  # Actually don't use the default for the dev env
  ports.lomas.userApiService = 48080;
  ports.lomas.adminApiService = 48081;

  lomas = {
    enable = true;
    serverHostAddr = "localhost";
    serverBindIp = "localhost";
    dashboard.host = "localhost";
    client.jupyter = {
      password = null; # "dprocks";
    };
  };

  lomas.oidc = {
    enable = true;
    providerUrl = "http://localhost:${config.ports.lomas.dex.api}/dex";
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
        redirect_uri = with config.lomas.dashboard; "http://${host}:${config.ports.streamlit}${baseUrl}/oauth2callback";
      };
      grafanaDashboard = {
        client_id = "lomas_grafana";
        client_secret = "lomas_grafana";
        redirect_uri = with config.lomas.telemetry.services.grafana; "http://${host}:${toString port}/login/generic_oauth";
      };
    };
  };

  lomas.dex = {
    enable = true;
    host = "localhost";
    address = "127.0.0.1";
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
    version = lib.mkDefault "3.14";
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

    # Config for sqlite backup (S3)
    LOMAS_SERVICE_backup__s3__bucket = "bucket";
    LOMAS_SERVICE_backup__s3__key_prefix = "backup";
    LOMAS_SERVICE_backup__s3__endpoint_url = "http://${config.lomas.garage.host}:${toString config.lomas.garage.port}";
    LOMAS_SERVICE_backup__s3__access_key_id = config.lomas.garage.keyId;
    LOMAS_SERVICE_backup__s3__secret_access_key = config.lomas.garage.secretKey;
    
    # Lomas Runtime
    LOMAS_SERVER_log_level = "INFO";
    LOMAS_SERVER_lomas_log_level = "DEBUG";
    LOMAS_SERVER_user_host_port = config.ports.lomas.userApiService;
    LOMAS_SERVER_admin_host_port = config.ports.lomas.adminApiService;
    LOMAS_SERVER_opendp_features = toPydanticSetting [
      "contrib"
      "idealized-numerics"
      "honest-but-curious"
    ];
    LOMAS_SERVER_worker_api_key = config.lomas.workerApiKey;
    LOMAS_SERVER_reload = config.lomas.reload;
    # Server Specifics
    LOMAS_SERVER_bind_ip = config.lomas.serverBindIp;
    LOMAS_SERVER_root_path = config.lomas.baseUrl;
    LOMAS_SERVER_time_attack__method = "jitter";
    LOMAS_SERVER_time_attack__magnitude = 1;
    LOMAS_SERVER_submit_limit = 300;
    LOMAS_SERVER_authenticator__authentication_type = if config.lomas.oidc.enable then "oidc" else "free_pass";
    LOMAS_SERVER_authenticator__oidc_discovery_url = "${config.lomas.oidc.discoveryUrl}";
    LOMAS_SERVER_authenticator__query_userinfo = "${lib.boolToString config.lomas.oidc.queryUserinfo}";
    LOMAS_SERVER_bootstrap = "deadbeef";
    LOMAS_SERVER_database_directory = "/tmp/lomas-db/";
    LOMAS_SERVER_data_directory = "${config.git.root}/server/data/";
    LOMAS_SERVER_clean_admin_database = "false";
    # Worker specifics
    LOMAS_SERVER_server_host_addr = config.lomas.serverHostAddr;

    # Lomas client environment
    LOMAS_CLIENT_OIDC_DISCOVERY_URL = config.lomas.oidc.discoveryUrl;
    LOMAS_CLIENT_USE_PASSWORD_FLOW = "true";
    LOMAS_CLIENT_APP_URL = "http://localhost:${config.ports.lomas.userApiService}";

    # Lomas demo setup
    LOMAS_ADMIN_external_url = "http://localhost:${config.ports.lomas.adminApiService}"; # public lomas service url from dashboard
    LOMAS_ADMIN_service_url = "http://localhost:${config.ports.lomas.adminApiService}";
    LOMAS_ADMIN_USER_YAML = user_yaml_path;
    LOMAS_ADMIN_DATASET_YAML = dataset_yaml_path;
    LOMAS_ADMIN_DEX_CONFIG__URL = "grpc://${config.lomas.dex.adminAddress}:${config.ports.lomas.dex.admin}";
    LOMAS_ADMIN_BOOTSTRAP = config.env.LOMAS_SERVER_bootstrap;
  }
  // (listToPydanticEnvVar "LOMAS_SERVER_private_db_credentials" [
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
