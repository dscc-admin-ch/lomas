import logging
import logging.config
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

logger_provider = LoggerProvider(
    resource=Resource.create(
        {
            "service.name": "lomas-server-app",
            "service.instance.id": "instance-1",
        }
    ),
)
set_logger_provider(logger_provider)

exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

logging.getLogger().setLevel(logging.DEBUG)
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)

LOG = logging.getLogger()
LOG.debug("This is a DEBUG log 2")
LOG.info("This is an INFO log 2")
LOG.warning("This is a WARNING log 2")
LOG.error("This is an ERROR log 2")
LOG.critical("This is a CRITICAL log 2")

