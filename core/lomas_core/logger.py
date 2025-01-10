import logging
import logging.config
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

import os
DEBUG_LOG_OTEL_TO_CONSOLE =True #= os.getenv("DEBUG_LOG_OTEL_TO_CONSOLE", 'False').lower() == 'true'
DEBUG_LOG_OTEL_TO_PROVIDER = True # os.getenv("DEBUG_LOG_OTEL_TO_PROVIDER", 'False').lower() == 'true'


logger_provider = LoggerProvider(
    resource=Resource.create(
        {
            "service.name": "lomas-server-app",
            "service.instance.id": "instance-1",
        }
    ),
)
set_logger_provider(logger_provider)

# if DEBUG_LOG_OTEL_TO_CONSOLE:
#     exporter = ConsoleLogExporter()
#     logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

if DEBUG_LOG_OTEL_TO_PROVIDER:
    exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))


logging.getLogger().setLevel(logging.DEBUG)
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)

LOG = logging.getLogger()
LOG.debug("This is a DEBUG log")
LOG.info("This is an INFO log")
LOG.warning("This is a WARNING log")
LOG.error("This is an ERROR log")
LOG.critical("This is a CRITICAL log")

