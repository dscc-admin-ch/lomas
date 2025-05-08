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

  # Networking
  mongo_addr = "localhost";
  mongo_port = 27017;
  minio_port = 19000;
  minio_console_port = 19001;
  rabbitmq_port = 5672;
  rabbitmq_mgmt_port = 15672; # spin the management interface http://localhost:15672 guest/guest
  rabbitmq_addr = "localhost";
  lomas_port = 48080;
  postgres_addr = "localhost";
  postgres_port = 5432;
  kc_https_port = 4443;
  kc_http_port = 4442;
  kc_management_port = 4441;
  kc_hostname = "localhost";
  dashboard_port = 8501;
  otel_port = 4317; # Must keep this value
  otel_port_http = 4318; # Must keep this value
  mongo_collector_port = 9216;
  jupyter_port = 8888;

  # RabbitMQ
  rabbitmq_user = "guest";
  rabbitmq_pass = "guest";

  # Keycloak
  kc_auth_realm = "master";
  kc_admin_client_id = "admin-cli";
  kc_setup_admin_user = "admin";
  kc_setup_admin_pwd = "admin";
  kc_setup_overwrite_realm = "true";

  lomas_realm = "lomas";
  lomas_admin_client_id = "lomas_admin";
  lomas_admin_client_secret = "lomas_admin";

  lomas_api_client_id = "lomas_api";
  lomas_api_client_secret = "lomas_api";

  # MongoDB
  mongo_root_user = "root";
  mongo_root_password = "root_pwd";
  mongo_db_name = "defaultdb";
  mongo_user = "user";
  mongo_password = "password";
  mongo_max_pool_size = 100;
  mongo_min_pool_size = 2;
  mongo_max_connecting = 2;

  # Minio
  minio_root_user = "admin";
  minio_root_pwd = "admin123";

  # Jupyter
  jupyter_pwd = "dprocks";

  # Demo data (relative to ./server/lomas_server since we run all scripts from there)
  admin_path_prefix = "${config.devenv.root}/server/data/";
  user_yaml_path = "/collections/user_collection.yaml";
  dataset_yaml_path = "/collections/dataset_collection.yaml";

  # Telemetry
  grafanaHost = "localhost";
  grafanaPort = 3000;
  prometheus_host = "localhost";
  prometheus_port = 19090;
  tempo_host = "localhost";
  tempo_http_port = 13200;
  tempo_grpc_port = 19095;
  tempo_otlp_grpc_port = 14317;
  loki_host = "localhost";
  loki_http_port = 13100;
  # loki_grpc_port = 19096;
  otlp_host = "localhost";
  otlp_metrics_port = 29090;
  mongodb_exporter_addr = "localhost";
  mongodb_exporter_port = 19216;
in
{
  overlays = import ./devenv/overlays.nix;
  # Environment variable available inside devenv
  env = {
    GREET = "Lomas env";
    KC_HOME_DIR = "${config.env.DEVENV_STATE}/keycloak";
    KC_CONF_DIR = "${config.env.DEVENV_STATE}/conf";
    KC_BOOTSTRAP_ADMIN_USERNAME = kc_setup_admin_pwd;
    KC_BOOTSTRAP_ADMIN_PASSWORD = kc_setup_admin_user;

    # Pydantic note:
    # Even when using a dotenv file, pydantic will still read environment variables as well as the dotenv file, environment variables will always take priority over values loaded from a dotenv file.

    # Lomas Server Runtime
    LOMAS_SERVICE_server__host_ip = "0.0.0.0";
    LOMAS_SERVICE_server__host_port = lomas_port;
    LOMAS_SERVICE_server__log_level = "info";
    LOMAS_SERVICE_server__reload = "true";
    LOMAS_SERVICE_server__submit_limit = 300;
    LOMAS_SERVICE_server__time_attack__method = "jitter";
    LOMAS_SERVICE_server__time_attack__magnitude = 1;

    LOMAS_SERVICE_amqp__url = "amqp://${rabbitmq_addr}:${toString rabbitmq_port}";
    LOMAS_SERVICE_amqp__username = rabbitmq_user;
    LOMAS_SERVICE_amqp__password = rabbitmq_pass;
    LOMAS_SERVICE_opendp_features = toPydanticSetting [
      "contrib"
      "floating-point"
      "honest-but-curious"
    ];
    LOMAS_SERVICE_admin_database__url = "mongodb://${mongo_addr}:${toString mongo_port}/${mongo_db_name}";
    LOMAS_SERVICE_admin_database__username = mongo_user;
    LOMAS_SERVICE_admin_database__password = mongo_password;
    LOMAS_SERVICE_admin_database__max_pool_size = mongo_max_pool_size;
    LOMAS_SERVICE_admin_database__min_pool_size = mongo_min_pool_size;
    LOMAS_SERVICE_admin_database__max_connecting = mongo_max_connecting;
    LOMAS_SERVICE_authenticator__authentication_type = "jwt";
    LOMAS_SERVICE_authenticator__keycloak_url = "http://localhost:${toString kc_http_port}";
    LOMAS_SERVICE_authenticator__realm = lomas_realm;
    LOMAS_SERVICE_private_db_credentials__0__credentials_name = "minio";
    LOMAS_SERVICE_private_db_credentials__0__db_type = "S3_DB";
    LOMAS_SERVICE_private_db_credentials__0__access_key_id = minio_root_user;
    LOMAS_SERVICE_private_db_credentials__0__secret_access_key = minio_root_pwd;

    LOMAS_SERVICE_telemetry__enabled = "false";
    LOMAS_SERVICE_telemetry__service_name = "lomas-server-app";
    LOMAS_SERVICE_telemetry__service_id = "default-host";
    LOMAS_SERVICE_telemetry__collector_endpoint = "http://localhost:${toString otel_port}";
    LOMAS_SERVICE_telemetry__collector_insecure = "true";

    # Lomas client environment
    LOMAS_CLIENT_KEYCLOAK_URL = "http://${kc_hostname}:${toString kc_http_port}";
    LOMAS_CLIENT_REALM = lomas_realm;
    LOMAS_CLIENT_APP_URL = "http://localhost:${toString lomas_port}";

    LOMAS_CLIENT_telemetry__enabled = "false";
    LOMAS_CLIENT_telemetry__service_name = "lomas-server-app";
    LOMAS_CLIENT_telemetry__service_id = "default-host";
    LOMAS_CLIENT_telemetry__collector_endpoint = "http://localhost:${toString otel_port}";
    LOMAS_CLIENT_telemetry__collector_insecure = "true";

    # Keycloak setup
    LOMAS_KC_SETUP_KEYCLOAK_URL = "http://${kc_hostname}:${toString kc_http_port}";
    LOMAS_KC_SETUP_KEYCLOAK_AUTHENTICATION_REALM = kc_auth_realm;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_CLIENT_ID = kc_admin_client_id;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_USER = kc_setup_admin_user;
    LOMAS_KC_SETUP_KEYCLOAK_ADMIN_PWD = kc_setup_admin_pwd;
    LOMAS_KC_SETUP_LOMAS_REALM = lomas_realm;
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_ID = lomas_admin_client_id;
    LOMAS_KC_SETUP_LOMAS_ADMIN_CLIENT_SECRET = lomas_admin_client_secret;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_ID = lomas_api_client_id;
    LOMAS_KC_SETUP_LOMAS_API_CLIENT_SECRET = lomas_api_client_secret;
    LOMAS_KC_SETUP_OVERWRITE_REALM = kc_setup_overwrite_realm;

    # Lomas demo setup
    LOMAS_ADMIN_server_url = "http://localhost:${toString lomas_port}"; # public lomas service url from dashboard
    LOMAS_ADMIN_server_service = "http://localhost:${toString lomas_port}";
    LOMAS_ADMIN_MG_CONFIG__url = "mongodb://localhost:${toString mongo_port}/${mongo_db_name}";
    LOMAS_ADMIN_MG_CONFIG__username = mongo_user;
    LOMAS_ADMIN_MG_CONFIG__password = mongo_password;
    LOMAS_ADMIN_KC_CONFIG__URL = "http://${kc_hostname}:${toString kc_http_port}";
    LOMAS_ADMIN_KC_CONFIG__REALM = lomas_realm;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_ID = lomas_admin_client_id;
    LOMAS_ADMIN_KC_CONFIG__CLIENT_SECRET = lomas_admin_client_secret;
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
    configItems = {
      "default_user" = rabbitmq_user;
      "default_pass" = rabbitmq_pass;
      "heartbeat" = "1800"; # Extra super duper long hearbeat timeout for long running tasks in workersss
    };
  };

  processes.rabbitmq.process-compose = {
    readiness_probe = {
      initial_delay_seconds = 20;
      timeout_seconds = 5;
      period_seconds = 5;
      success_threshold = 2;
      failure_threshold = 10;
    };
  };

  ##########
  # SERVER #
  ##########

  processes.lomas-server = {
    exec = "python uvicorn_serve.py";
    process-compose = {
      working_dir = "$DEVENV_ROOT/server/lomas_server";
      depends_on.mongodb.condition = "process_healthy";
    };
  };

  #############
  # DASHBOARD #
  #############

  processes.admin-dashboad = {
    exec = "streamlit run --server.headless true lomas_server/administration/dashboard/about.py";
    process-compose = {
      working_dir = "$DEVENV_ROOT/server";
      environment = [
        "STREAMLIT_SERVER_PORT=${toString dashboard_port}"
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS=0"
      ];
    };
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
      # log_location = "$DEVENV_ROOT/worker.log";
    };
  };

  ###########
  # MONGODB #
  ###########

  services.mongodb = {
    enable = true;
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
      mongo_user
      mongo_password
      ;
    inherit (config.services.mongodb) initDatabaseUsername initDatabasePassword;
  };

  ########
  # OTLP #
  ########

  # tune down default namespace from "all" to "default" to make telemetry namespace optional, see @yelp
  process.manager.args = {
    namespace = "default";
  };

  services.opentelemetry-collector = {
    enable = true;
    settings = {
      receivers.otlp.protocols = {
        grpc.endpoint = "localhost:${toString otel_port}";
        http.endpoint = "localhost:${toString otel_port_http}";
      };

      processors.batch.timeout = "5s";

      exporters = {
        debug.verbosity = "detailed";

        prometheus = {
          endpoint = "${otlp_host}:${toString otlp_metrics_port}";
          namespace = "lomas_server";
        };

        "otlp/tempo" = {
          endpoint = "${tempo_host}:${toString tempo_otlp_grpc_port}";
          tls.insecure = true;
        };

        "otlphttp/loki" = {
          endpoint = "http://${loki_host}:${toString loki_http_port}/otlp";
          tls.insecure = true;
        };
      };

      extensions = {
        health_check.endpoint = "localhost:13133";
        pprof.endpoint = "localhost:1777";
        zpages.endpoint = "localhost:55679";
      };

      service = {
        extensions = [
          "health_check"
          "pprof"
          "zpages"
        ];
        pipelines = {
          traces = {
            receivers = [ "otlp" ];
            processors = [ "batch" ];
            exporters = [
              "debug"
              "otlp/tempo"
            ];
          };
          metrics = {
            receivers = [ "otlp" ];
            processors = [ "batch" ];
            exporters = [
              "debug"
              "prometheus"
            ];
          };
          logs = {
            receivers = [ "otlp" ];
            processors = [ "batch" ];
            exporters = [
              "debug"
              "otlphttp/loki"
            ];
          };
        };
      };

    };
  };

  processes.opentelemetry-collector.process-compose = {
    namespace = "telemetry";
    depends_on = {
      tempo.condition = "process_started";
      loki.condition = "process_started";
      prometheus.condition = "process_started";
    };
  };

  services.prometheus = {
    enable = true;
    port = prometheus_port;
    globalConfig = {
      evaluation_interval = "10s";
      scrape_interval = "10s";
      scrape_timeout = "10s";
    };
    scrapeConfigs = [
      {
        job_name = "prometheus";
        static_configs = [ { targets = [ "localhost:${toString prometheus_port}" ]; } ];
      }
      {
        job_name = "tempo";
        static_configs = [ { targets = [ "localhost:${toString tempo_http_port}" ]; } ];
      }
      {
        job_name = "otel-collector";
        static_configs = [ { targets = [ "localhost:${toString otlp_metrics_port}" ]; } ];
      }
      {
        job_name = "loki";
        static_configs = [ { targets = [ "localhost:${toString loki_http_port}" ]; } ];
      }
      {
        job_name = "mongodb";
        static_configs = [ { targets = [ "localhost:${toString mongodb_exporter_port}" ]; } ];
      }
    ];
  };
  processes.prometheus.process-compose.namespace = "telemetry";

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
  # cheeky override of postgres statup command to force a clean start
  processes.postgres.process-compose.command = "rm -rvf ${config.env.PGDATA} && ${config.processes.postgres.exec}";

  # Keycloak setup for lomas
  processes.keycloak_setup = {
    exec = "lomas-keycloak-setup";
    process-compose = {
      working_dir = "$DEVENV_ROOT/server/lomas_server";
      depends_on.keycloak.condition = "process_healthy";
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
      accessKey = minio_root_user;
      secretKey = minio_root_pwd;
      inherit listenAddress;
      buckets = [ "example" ];
      afterStart = ''
        mc cp ${./server/lomas_server/tests/test_data/test_penguin.csv} myminio/example/data/test_penguin.csv
        mc cp ${./server/lomas_server/tests/test_data/metadata/penguin_metadata.yaml}  myminio/example/metadata/penguin_metadata.yaml
        mc cp ${./server/data/datasets/titanic.csv} myminio/example/data/titanic.csv
        mc cp ${./server/data/collections/metadata/titanic_metadata.yaml}  myminio/example/metadata/titanic_metadata.yaml
        mc ls --recursive --versions myminio/example
      '';
      # Configure myminio alias
      clientConfig = {
        aliases.myminio = {
          url = "http://${listenAddress}"; # <scheme>:// is mandatory
          accessKey = minio_root_user;
          secretKey = minio_root_pwd;
          api = "S3v4";
          path = "auto";
        };
      };
    };

  ##############
  # Monitoring #
  ##############

  processes.grafana =
    let
      working_dir = "${config.env.DEVENV_STATE}/grafana";

      datasources = pkgs.writeText "grafana-config.yaml" ''
        datasources:
        - name: Prometheus
          type: prometheus
          uid: prometheus
          access: proxy
          orgId: 1
          url: 'http://${prometheus_host}:${toString prometheus_port}'
          basicAuth: false
          isDefault: false
          version: 1
          editable: true
          jsonData:
            httpMethod: GET

        - name: Tempo
          type: tempo
          uid: tempo
          access: proxy
          orgId: 1
          url: 'http://${tempo_host}:${toString tempo_http_port}'
          basicAuth: false
          isDefault: true
          version: 1
          editable: true
          apiVersion: 1
          stream_over_http_enabled: false

        - name: Loki
          type: loki
          uid: loki
          access: proxy
          orgId: 1
          url: 'http://${loki_host}:${toString loki_http_port}'
          basicAuth: false
          isDefault: false
          version: 1
          editable: true
          jsonData:
            httpHeaderName1: X-Scope-OrgID
          secureJsonData:
            httpHeaderValue1: tenant1
      '';

      conf = pkgs.writeText "config.ini" ''
        [server]
        domain=${grafanaHost}
        enforce_domain=false
        http_port=${toString grafanaPort}
        enable_gzip=false

        [paths]
        enable_gzip=true
        http_addr=${grafanaHost}
        http_port=${toString grafanaPort}
        plugins=${working_dir}/plugins
        provisioning=${working_dir}/provisioning
        server=http

        [snapshots]
        external_enabled=false
        public_mode=false

        [security]
        admin_user=admin
        admin_password=admin
        disable_initial_admin_creation=true
      '';

      dashboardProvision = writeYAML "dashboard.yaml" {
        apiVersion = 1;
        providers = [
          {
            name = "Lomas";
            folder = "Services";
            type = "file";
            options.path = "${working_dir}/dashboards";
          }
        ];
      };

      extraFlags = [ ];
    in
    {
      exec = ''
        mkdir -p ${working_dir}/dashboards
        mkdir -p ${working_dir}/provisioning/{datasources,dashboards}

        ln -fs ${pkgs.grafana}/share/grafana/conf ${working_dir}
        ln -fs ${pkgs.grafana}/share/grafana/public ${working_dir}

        ln -sf ${datasources} ${working_dir}/provisioning/datasources/datasource.yaml
        ln -sf ${dashboardProvision} ${working_dir}/provisioning/dashboards/dashboard.yaml
        ln -sf ${./server/configs/observability/grafana/example_dashboard_config.json} ${working_dir}/dashboards
        ln -sf ${conf} ${working_dir}/grafana.ini

        ${pkgs.grafana}/bin/grafana server -homepath=${working_dir} -config=${conf} ${lib.escapeShellArgs extraFlags}
      '';
      process-compose.namespace = "telemetry";
    };

  processes.tempo =
    let
      working_dir = "${config.env.DEVENV_STATE}/tempo";
      conf = writeYAML "config-tempo.yaml" {
        stream_over_http_enabled = true;
        server = {
          http_listen_port = tempo_http_port;
          http_listen_address = tempo_host;
          grpc_listen_port = tempo_grpc_port;
          grpc_listen_address = tempo_host;
          log_level = "info";
        };
        # query_frontend.search.duration_slo = "5s";
        # query_frontend.search.throughput_bytes_slo = 1.073741824e+09;
        # query_frontend.search.metadata_slo.duration_slo = "5s";
        # query_frontend.search.metadata_slo.throughput_bytes_slo = 1.073741824e+09;
        # query_frontend.trace_by_id.duration_slo = "5s";
        distributor.receivers.otlp.protocols.grpc.endpoint = "${tempo_host}:${toString tempo_otlp_grpc_port}";
        ingester.max_block_duration = "5m";
        compactor.compaction.block_retention = "1h";
        metrics_generator.registry.external_labels.source = "tempo";
        metrics_generator.storage.path = "${working_dir}/generator/wal";
        metrics_generator.storage.remote_write = [
          {
            url = "http://${prometheus_host}:${toString prometheus_port}/api/v1/write";
            send_exemplars = true;
          }
        ];
        metrics_generator.traces_storage.path = "${working_dir}/generator/traces";
        storage.trace.backend = "local";
        storage.trace.wal.path = "${working_dir}/wal";
        storage.trace.local.path = "${working_dir}/blocks";
        overrides.defaults.metrics_generator.processors = [
          "service-graphs"
          "span-metrics"
          "local-blocks"
        ];
        overrides.defaults.metrics_generator.generate_native_histograms = "both";
      };
      extraFlags = [ ];
    in
    {
      exec = "${pkgs.tempo}/bin/tempo --config.file=${conf} ${lib.escapeShellArgs extraFlags}";
      process-compose.namespace = "telemetry";
    };

  processes.loki =
    let
      working_dir = "${config.env.DEVENV_STATE}/loki";
      conf = writeYAML "config-loki.yaml" {
        auth_enabled = false;
        limits_config.allow_structured_metadata = true;
        limits_config.volume_enabled = true;
        server.http_listen_port = loki_http_port;
        # server.grpc_listen_port = loki_grpc_port;
        common.ring.instance_addr = loki_host;
        common.ring.kvstore.store = "inmemory";
        common.replication_factor = 1;
        common.path_prefix = working_dir;
        schema_config.configs = [
          {
            from = "2025-01-10";
            store = "tsdb";
            object_store = "filesystem";
            schema = "v13";
            index.prefix = "loki_index_";
            index.period = "24h";
          }
        ];
        storage_config.tsdb_shipper.active_index_directory = "${working_dir}/index";
        storage_config.tsdb_shipper.cache_location = "${working_dir}/index_cache";
        storage_config.filesystem.directory = "${working_dir}/chunks";
        pattern_ingester.enabled = true;
      };
      extraFlags = [ ];
    in
    {
      exec = "${pkgs.grafana-loki}/bin/loki --config.file=${conf} ${lib.escapeShellArgs extraFlags}";
      process-compose.namespace = "telemetry";
    };

  processes.mongodb-exporter =
    let
      inherit (config.services.mongodb) initDatabaseUsername initDatabasePassword;
      uri = "mongodb://${initDatabaseUsername}:${initDatabasePassword}@${mongo_addr}:${toString mongo_port}";
    in
    {
      exec = ''
        ${lib.getExe pkgs.prometheus-mongodb-exporter} \
        --mongodb.uri="${uri}" \
        --collect-all \
        --web.listen-address="${mongodb_exporter_addr}:${toString mongodb_exporter_port}" \
        --web.telemetry-path="/metrics"
      '';
      process-compose.namespace = "telemetry";
    };

  #############
  # GIT HOOKS #
  #############

  git-hooks.hooks = import ./devenv/hooks.nix {
    inherit pkgs;
    env = config.env;
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
        LOMAS_SERVICE_PORT=${toString lomas_port}

        # Keycloak
        LOMAS_KC_PORT=${toString kc_http_port}
        LOMAS_KC_ADMIN_USER=${kc_setup_admin_user}
        LOMAS_KC_ADMIN_PWD=${kc_setup_admin_pwd}

        # RabbitMQ
        LOMAS_RABBIT_MQ_PORT=${toString rabbitmq_port}
        LOMAS_RABBIT_MQ_MGMT_PORT=${toString rabbitmq_mgmt_port}
        LOMAS_RABBIT_MQ_USER=${rabbitmq_user}
        LOMAS_RABBIT_MQ_PASS=${rabbitmq_pass}

        # MongoDB
        LOMAS_MONGO_PORT=${toString mongo_port}
        LOMAS_MONGO_ROOT_USER=${mongo_root_user}
        LOMAS_MONGO_ROOT_PWD=${mongo_root_password}
        LOMAS_MONGO_DATABASE=${mongo_db_name}

        # Dashboard
        LOMAS_DASHBOARD_PORT=${toString dashboard_port}

        # MinIO
        LOMAS_MINIO_PORT=${toString minio_port}
        LOMAS_MINIO_CONSOLE_PORT=${toString minio_console_port}
        LOMAS_MINIO_ROOT_USER=${minio_root_user}
        LOMAS_MINIO_ROOT_PWD=${minio_root_pwd}

        # Telemetry
        LOMAS_OTEL_PORT=${toString otel_port}
        LOMAS_MONGO_COLLECTOR_PORT=${toString mongo_collector_port}

        # Client
        LOMAS_CLIENT_PORT=${toString jupyter_port}
        EOF
      '';
    };

    "filegen:env_docker_compose_service" =
      let
        kcEnvVar = lib.filterAttrs (name: value: lib.strings.hasPrefix "LOMAS_SERVICE_" name) config.env;
        kcEnvVarFinal = kcEnvVar // {
          LOMAS_SERVICE_amqp__url = "amqp://rabbitmq:${toString rabbitmq_port}";
          LOMAS_SERVICE_authenticator__keycloak_url = "http://keycloak:${toString kc_http_port}";
          LOMAS_SERVICE_admin_database__url = "mongodb://mongodb:${toString mongo_port}/${mongo_db_name}";
          LOMAS_SERVICE_telemetry__collector_endpoint = "http://otel-collector:${toString otel_port}";
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
          LOMAS_CLIENT_APP_URL = "http://lomas_server:${toString lomas_port}";
          LOMAS_CLIENT_KEYCLOAK_URL = "http://keycloak:${toString kc_http_port}";
          LOMAS_CLIENT_telemetry__collector_endpoint = "http://otel-collector:${toString otel_port}";
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
          LOMAS_KC_SETUP_KEYCLOAK_URL = "http://keycloak:${toString kc_http_port}";
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
          LOMAS_ADMIN_KC_CONFIG__URL = "http://keycloak:${toString kc_http_port}";
          LOMAS_ADMIN_MG_CONFIG__URL = "mongodb://mongodb:${toString mongo_port}/${mongo_db_name}";
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
          user: "${mongo_user}",
          pwd: "${mongo_password}",
          roles: [{ role: "readWrite", db: "${mongo_db_name}" }]}
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
      working_dir = "$DEVENV_ROOT/";
      pc-config-patch = writeYAML "pc-coverage-disable-worker.yaml" {
        processes = {
          # patch/override worker definition to force 1 instance and run coverage on it
          worker = {
            inherit working_dir;
            replicas = 1;
            command = "coverage run --rcfile=pyproject.toml -p -m lomas_server.worker";
          };
          # Add this ad-hoc pytest process to be run in foreground whilst ensuring
          # all background dependencies
          pytest-cov = {
            inherit working_dir;
            command = "pytest --cov --no-cov-on-fail --cov-config=pyproject.toml \${1:-.}";
            depends_on = {
              worker.condition = "process_started";
              minio.condition = "process_started";
              mongodb.condition = "process_started";
              mongodb-configure.condition = "process_completed_successfully";
              keycloak.condition = "process_ready";
              rabbitmq.condition = "process_ready";
              keycloak_setup.condition = "process_completed_successfully";
              lomas-server.condition = "process_started";
            };
            # We terminate the whole process-compose at the end of this task
            availability.exit_on_end = true;
          };
        };
      };
    in
    ''
      path=''${@:-.}
      pushd ${working_dir}
      echo "Running coverage on $path with patched process-compose config (${pc-config-patch})"
      yq -Poy ${pc-config-patch}
      process-compose run pytest-cov -f $PC_CONFIG_FILES -f ${pc-config-patch} -- "$path"
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
    pushd $DEVEN_ROOT
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
