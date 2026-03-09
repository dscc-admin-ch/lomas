{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.lomas.telemetry;

  toYAML = lib.generators.toYAML { };
  writeYAML = filename: attrset: pkgs.writeText filename (toYAML attrset);

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  serviceModule =
    { config, name, ... }:
    {
      options = {
        host = mkOption {
          type = types.str;
          example = "1.2.3.4";
          description = "hostname / IP of the service host";
        };
        port = mkOption {
          type = types.nullOr types.port;
          default = null;
          example = 8080;
          description = "port number of the service host";
        };
        ports = mkOption {
          type = types.nullOr types.attrs;
          default = null;
          example = {
            http = 19080;
            grpc = 9095;
          };
          description = "ports mapping of the service";
        };
      };
    };
in
{
  options.lomas.telemetry = {
    enable = mkEnableOption "Enable lomas Telemetry Stack";

    services = mkOption {
      type = types.attrsOf (types.submodule serviceModule);
    };

  };

  config = mkIf cfg.enable {
    assertions = lib.mapAttrsToList (service: cfg: {
      assertion = lib.xor (cfg.port == null) (cfg.ports == null);
      message = "${service}: must define exactly one of (single) port or (port mapping) ports.";
    }) cfg.services;

    services.opentelemetry-collector = {
      enable = true;
      settings = {
        receivers.otlp.protocols = {
          grpc.endpoint = "localhost:${toString cfg.services.otlp.ports.grpc}";
          http.endpoint = "localhost:${toString cfg.services.otlp.ports.http}";
        };

        processors.batch.timeout = "5s";

        exporters = {
          debug.verbosity = "detailed";

          prometheus = {
            endpoint = "${cfg.services.otlp.host}:${toString cfg.services.otlp.ports.metrics}";
            namespace = "lomas_server";
          };

          "otlp/tempo" = {
            endpoint = "${cfg.services.tempo.host}:${toString cfg.services.tempo.ports.otlp_grpc}";
            tls.insecure = true;
          };

          "otlphttp/loki" = {
            endpoint = "http://${cfg.services.loki.host}:${toString cfg.services.loki.port}/otlp";
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

    processes.opentelemetry-collector = {
      after = [
        "devenv:processes:tempo@started"
        "devenv:processes:loki@started"
        "devenv:processes:prometheus@started"
      ];
    };

    services.prometheus = {
      enable = true;
      port = cfg.services.prometheus.port;
      globalConfig = {
        evaluation_interval = "10s";
        scrape_interval = "10s";
        scrape_timeout = "10s";
      };
      scrapeConfigs = [
        {
          job_name = "prometheus";
          static_configs = [ { targets = [ "localhost:${toString cfg.services.prometheus.port}" ]; } ];
        }
        {
          job_name = "tempo";
          static_configs = [ { targets = [ "localhost:${toString cfg.services.tempo.ports.http}" ]; } ];
        }
        {
          job_name = "otel-collector";
          static_configs = [ { targets = [ "localhost:${toString cfg.services.otlp.ports.metrics}" ]; } ];
        }
        {
          job_name = "loki";
          static_configs = [ { targets = [ "localhost:${toString cfg.services.loki.port}" ]; } ];
        }
      ];
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
            url: 'http://${cfg.services.prometheus.host}:${toString cfg.services.prometheus.port}'
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
            url: 'http://${cfg.services.tempo.host}:${toString cfg.services.tempo.ports.http}'
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
            url: 'http://${cfg.services.loki.host}:${toString cfg.services.loki.port}'
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
          domain=${cfg.services.grafana.host}
          enforce_domain=false
          http_port=${toString cfg.services.grafana.port}
          enable_gzip=false

          [paths]
          enable_gzip=true
          http_addr=${cfg.services.grafana.host}
          http_port=${toString cfg.services.grafana.port}
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
          ln -sf ${../server/configs/observability/grafana/example_dashboard_config.json} ${working_dir}/dashboards
          ln -sf ${conf} ${working_dir}/grafana.ini

          ${pkgs.grafana}/bin/grafana server -homepath=${working_dir} -config=${conf} ${lib.escapeShellArgs extraFlags}
        '';
      };

    processes.tempo =
      let
        working_dir = "${config.env.DEVENV_STATE}/tempo";
        conf = writeYAML "config-tempo.yaml" {
          stream_over_http_enabled = true;
          server = {
            http_listen_port = cfg.services.tempo.ports.http;
            http_listen_address = cfg.services.tempo.host;
            grpc_listen_port = cfg.services.tempo.ports.grpc;
            grpc_listen_address = cfg.services.tempo.host;
            log_level = "info";
          };
          # query_frontend.search.duration_slo = "5s";
          # query_frontend.search.throughput_bytes_slo = 1.073741824e+09;
          # query_frontend.search.metadata_slo.duration_slo = "5s";
          # query_frontend.search.metadata_slo.throughput_bytes_slo = 1.073741824e+09;
          # query_frontend.trace_by_id.duration_slo = "5s";
          distributor.receivers.otlp.protocols.grpc.endpoint =
            "${cfg.services.tempo.host}:${toString cfg.services.tempo.ports.otlp_grpc}";
          ingester.max_block_duration = "5m";
          compactor.compaction.block_retention = "1h";
          metrics_generator.registry.external_labels.source = "tempo";
          metrics_generator.storage.path = "${working_dir}/generator/wal";
          metrics_generator.storage.remote_write = [
            {
              url = "http://${cfg.services.prometheus.host}:${toString cfg.services.prometheus.port}/api/v1/write";
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
      };

    processes.loki =
      let
        working_dir = "${config.env.DEVENV_STATE}/loki";
        conf = writeYAML "config-loki.yaml" {
          auth_enabled = false;
          limits_config.allow_structured_metadata = true;
          limits_config.volume_enabled = true;
          server.http_listen_port = cfg.services.loki.port;
          # server.grpc_listen_port = loki_grpc_port;
          common.ring.instance_addr = cfg.services.loki.host;
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
          storage_config = {
            tsdb_shipper.active_index_directory = "${working_dir}/index";
            tsdb_shipper.cache_location = "${working_dir}/index_cache";
            filesystem.directory = "${working_dir}/chunks";
          };
          pattern_ingester.enabled = true;
        };
        extraFlags = [ ];
      in
      {
        exec = "${pkgs.grafana-loki}/bin/loki --config.file=${conf} ${lib.escapeShellArgs extraFlags}";
      };

  };
}
