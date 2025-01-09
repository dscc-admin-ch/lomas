import logging
import logging.config
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

import os
DEBUG_LOG_OTEL_TO_CONSOLE =True #= os.getenv("DEBUG_LOG_OTEL_TO_CONSOLE", 'False').lower() == 'true'
DEBUG_LOG_OTEL_TO_PROVIDER = True # os.getenv("DEBUG_LOG_OTEL_TO_PROVIDER", 'False').lower() == 'true'


class FormattedLoggingHandler(LoggingHandler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        record.msg = msg
        record.args = None
        self._logger.emit(self._translate(record))

def otel_logging_init():
    log_level = str(os.getenv("OTEL_PYTHON_LOG_LEVEL", "INFO")).upper()
    if (log_level == "CRITICAL"):
        log_level = logging.CRITICAL
        print(f"Using log level: CRITICAL / {log_level}")
    elif (log_level == "ERROR"):
        log_level = logging.ERROR
        print(f"Using log level: ERROR / {log_level}")
    elif (log_level == "WARNING"):
        log_level = logging.WARNING
        print(f"Using log level: WARNING / {log_level}")
    elif (log_level == "INFO"):
        log_level = logging.INFO
        print(f"Using log level: INFO / {log_level}")
    elif (log_level == "DEBUG"):
        log_level = logging.DEBUG
        print(f"Using log level: DEBUG / {log_level}")
    elif (log_level == "NOTSET"):
        log_level = logging.INFO
        print(f"Using log level: NOTSET / {log_level}")


resource = Resource(attributes={"app.name": "lomas_server_log"})

logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
# if DEBUG_LOG_OTEL_TO_CONSOLE:
#     console_log_exporter = ConsoleLogExporter()
#     logger_provider.add_log_record_processor(SimpleLogRecordProcessor(console_log_exporter))

if DEBUG_LOG_OTEL_TO_PROVIDER:
    otlp_log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))


otel_log_handler = FormattedLoggingHandler(logger_provider=logger_provider)
LoggingInstrumentor().instrument()
logFormatter = logging.Formatter(os.getenv("OTEL_PYTHON_LOG_FORMAT", None))
otel_log_handler.setFormatter(logFormatter)
logging.getLogger().addHandler(otel_log_handler)

LOG = logging.getLogger()
LOG.debug("Quick zephyrs blow, vexing daft Jim.")
LOG.info("How quickly daft jumping zebras vex.")

