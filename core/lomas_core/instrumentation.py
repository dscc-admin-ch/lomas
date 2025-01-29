import logging
import logging.config

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from lomas_core.constants import OTLP_COLLECTOR_ENDPOINT


def get_ressource(service_name: str, host_name: str):
    """
    Creates a Resource object with metadata describing the service.

    Returns:
        Resource: The resource object containing service metadata.
    """
    return Resource.create({"service.name": service_name, "service.instance.id": host_name})


def init_traces_exporter(resource: Resource) -> None:
    """
    Initializes the OpenTelemetry trace exporter with a given resource.

    Args:
        resource (Resource): The resource to associate with the trace telemetry.
    """
    exporter = OTLPSpanExporter(endpoint=OTLP_COLLECTOR_ENDPOINT, insecure=True)
    span_processor = BatchSpanProcessor(exporter)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)


def init_metrics_exporter(resource: Resource) -> None:
    """
    Initializes the OpenTelemetry metrics exporter with a given resource.

    Args:
        resource (Resource): The resource to associate with the metric telemetry.
    """
    exporter = OTLPMetricExporter(endpoint=OTLP_COLLECTOR_ENDPOINT, insecure=True)
    reader = PeriodicExportingMetricReader(exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)


def init_logs_exporter(resource: Resource) -> None:
    """
    Initializes the OpenTelemetry logs exporter with a given resource.

    Args:
        resource (Resource): The resource to associate with the log telemetry.
    """
    exporter = OTLPLogExporter(endpoint=OTLP_COLLECTOR_ENDPOINT, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    logging.getLogger().setLevel(logging.DEBUG)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)


def init_telemetry(resource: Resource) -> None:
    """
    Initializes all OpenTelemetry exporters with a shared resource.

    Args:
        resource (Resource): The resource to associate with the app and instance.
    """

    init_traces_exporter(resource)
    init_metrics_exporter(resource)
    init_logs_exporter(resource)
