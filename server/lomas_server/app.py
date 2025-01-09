from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from starlette.middleware.base import BaseHTTPMiddleware


from lomas_core.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_core.logger import LOG
from lomas_core.models.constants import AdminDBType
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import add_demo_data_to_mongodb_admin
from lomas_server.admin_database.yaml_database import AdminYamlDatabase
from lomas_server.constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    SERVER_LIVE,
)
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.utils.config import get_config


@asynccontextmanager
async def lifespan(lomas_app: FastAPI) -> AsyncGenerator:
    """
    Lifespan function for the server.

    This function is executed once on server startup, yields and
    finishes running at server shutdown.

    Server initialization is performed (config loading, etc.) and
    the server state is updated accordingly. This can have potential
    side effects on the return values of the "depends"
    functions, which check the server state.
    """
    # Startup
    LOG.info("Startup message")

    # Set some app state
    lomas_app.state.admin_database = None

    # General server state, can add fields if need be.
    lomas_app.state.server_state = {
        "state": [],
        "message": [],
        "LIVE": False,
    }
    lomas_app.state.server_state["state"].append("Startup event")

    status_ok = True
    # Load config
    try:
        LOG.info("Loading config")
        lomas_app.state.server_state["message"].append("Loading config")
        config = get_config()
        lomas_app.state.private_credentials = config.private_db_credentials
    except InternalServerException:
        LOG.info("Config could not loaded")
        lomas_app.state.server_state["state"].append(CONFIG_NOT_LOADED)
        lomas_app.state.server_state["message"].append("Server could not be started!")
        lomas_app.state.server_state["LIVE"] = False
        status_ok = False

    # Fill up user database if in develop mode ONLY
    if status_ok and config.develop_mode:
        LOG.info("!! Develop mode ON !!")
        lomas_app.state.server_state["message"].append("!! Develop mode ON !!")
        if config.admin_database.db_type == AdminDBType.MONGODB:
            LOG.info("Adding demo data to MongoDB Admin")
            lomas_app.state.server_state["message"].append("Adding demo data to MongoDB Admin")
            add_demo_data_to_mongodb_admin()

    # Load admin database
    if status_ok:
        try:
            LOG.info("Loading admin database")
            lomas_app.state.server_state["message"].append("Loading admin database")
            lomas_app.state.admin_database = admin_database_factory(config.admin_database)
        except InternalServerException as e:
            LOG.exception(f"Failed at startup: {str(e)}")
            lomas_app.state.server_state["state"].append(DB_NOT_LOADED)
            lomas_app.state.server_state["message"].append(f"Admin database could not be loaded: {str(e)}")
            lomas_app.state.server_state["LIVE"] = False
            status_ok = False

        lomas_app.state.server_state["state"].append("Startup completed")
        lomas_app.state.server_state["message"].append("Startup completed")

    # Set DP Libraries config
    set_opendp_features_config(config.dp_libraries.opendp)

    if status_ok:
        LOG.info("Server start condition OK")
        lomas_app.state.server_state["state"].append(SERVER_LIVE)
        lomas_app.state.server_state["message"].append("Server start condition OK")
        lomas_app.state.server_state["LIVE"] = True

    yield  # lomas_app is handling requests

    # Shutdown event
    if isinstance(lomas_app.state.admin_database, AdminYamlDatabase):
        lomas_app.state.admin_database.save_current_database()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get the current span in the context
        tracer = trace.get_tracer(__name__)
        span = tracer.start_span("HTTP Request")

        # Attach custom attributes or log information on the span
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.client_ip", request.client.host)
        user_name = request.headers.get("user_name", "unknown")
        span.set_attribute("user_name", user_name)
        LOG.info(f"0 Request received: {request.method} {request.url}")

        # Log a message (optional, you can use any logging framework here)
        print(f"1 Request received: {request.method} {request.url}")

        try:
            # Call the next middleware or route handler
            response = await call_next(request)
        finally:
            # End the span after the response is returned
            span.end()

        return response

resource = Resource(attributes={"app.name": "lomas_server"})

# Initialize OpenTelemetry Traces
DEBUG_TRACES_OTEL_TO_CONSOLE = False
DEBUG_TRACES_OTEL_TO_PROVIDER = True

tracer_provider = TracerProvider(resource=resource)

if DEBUG_TRACES_OTEL_TO_CONSOLE:
    otlp_trace_exporter = ConsoleSpanExporter()

if DEBUG_TRACES_OTEL_TO_PROVIDER:
    otlp_trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", timeout=10, insecure=True)


span_processor = BatchSpanProcessor(otlp_trace_exporter)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

# Initialize OpenTelemetry Metrics
DEBUG_METRIC_OTEL_TO_CONSOLE = False
DEBUG_METRIC_OTEL_TO_PROVIDER = True

if DEBUG_METRIC_OTEL_TO_CONSOLE:
    exporter = ConsoleMetricExporter()

if DEBUG_METRIC_OTEL_TO_PROVIDER:
    exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)

reader = PeriodicExportingMetricReader(exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meter_provider)

LOG.info(f"THIS IS A TEST")

# This object holds the server object
app = FastAPI(lifespan=lifespan)
app.add_middleware(LoggingMiddleware)

# Add custom exception handlers
add_exception_handlers(app)

# Instrument the FastAPI app for tracing, metrics, and logging
FastAPIInstrumentor.instrument_app(
    app, tracer_provider=tracer_provider, meter_provider=meter_provider
)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)