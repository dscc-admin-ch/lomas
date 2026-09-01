{ lib, ... }:
let
  portStr = with lib.types; coercedTo port toString str;
in
{
  # Option which (can) have farther reaching implications than local dev environment
  # like public/service port needed to build/package CI-test / infra

  options = {
    ports.otlp = {
      grpc = lib.mkOption {
        type = portStr;
        default = 4317;
        description = ''
          Default port for OTLP/gRPC
          (As per OTLP Spec. 1.11.0 @ https://opentelemetry.io/docs/specs/otlp/ )
        '';
      };
      http = lib.mkOption {
        type = portStr;
        default = 4318;
        description = ''
          Default port for OTLP/HTTP
          (As per OTLP Spec. 1.11.0 @ https://opentelemetry.io/docs/specs/otlp/ )
        '';
      };
    };

    ports.lomas = {
      userApiService = lib.mkOption {
        type = portStr;
        default = 8080;
        description = "Default (Service/Exposed) port Lomas HTTP(s) user API";
      };

      adminApiService = lib.mkOption {
        type = portStr;
        default = 8081;
        description = "Default (Service/Exposed) port Lomas HTTP(s) admin API";
      };

      dex = {
        api = lib.mkOption {
          type = portStr;
          default = 4445;
          description = "Default dex API port (?src?)";
        };
        admin = lib.mkOption {
          type = portStr;
          default = 4446;
          description = "Default dex Admin API port (?src?)";
        };
      };
    };

    ports.streamlit = lib.mkOption {
      type = portStr;
      default = 8501;
      description = "Default Streamlit port (Unofficial)";
    };

    ports.jupyter = lib.mkOption {
      type = portStr;
      default = 8888;
      description = "Default (local) Jupyter Server port";
    };

  };
}
