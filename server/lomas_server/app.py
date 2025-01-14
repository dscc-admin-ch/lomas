import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI, Request

from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from starlette.middleware.base import BaseHTTPMiddleware

from lomas_core.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_core.instrumentation import get_ressource, init_telemetry
from lomas_core.models.constants import AdminDBType
from lomas_core.telemetry import LOG
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import add_demo_data_to_mongodb_admin
from lomas_server.admin_database.yaml_database import AdminYamlDatabase
from lomas_server.constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    SERVER_LIVE,
    SERVER_SERVICE_NAME,
    SERVICE_ID,
)
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.utils.config import get_config
from lomas_server.utils.metrics import MetricMiddleware


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
    logging.info("Startup message")

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
        logging.info("Loading config")
        lomas_app.state.server_state["message"].append("Loading config")
        config = get_config()
        lomas_app.state.private_credentials = config.private_db_credentials
    except InternalServerException:
        logging.info("Config could not loaded")
        lomas_app.state.server_state["state"].append(CONFIG_NOT_LOADED)
        lomas_app.state.server_state["message"].append("Server could not be started!")
        lomas_app.state.server_state["LIVE"] = False
        status_ok = False

    # Fill up user database if in develop mode ONLY
    if status_ok and config.develop_mode:
        logging.info("!! Develop mode ON !!")
        lomas_app.state.server_state["message"].append("!! Develop mode ON !!")
        if config.admin_database.db_type == AdminDBType.MONGODB:
            logging.info("Adding demo data to MongoDB Admin")
            lomas_app.state.server_state["message"].append("Adding demo data to MongoDB Admin")
            add_demo_data_to_mongodb_admin()

    # Load admin database
    if status_ok:
        try:
            logging.info("Loading admin database")
            lomas_app.state.server_state["message"].append("Loading admin database")
            lomas_app.state.admin_database = admin_database_factory(config.admin_database)
        except InternalServerException as e:
            logging.exception(f"Failed at startup: {str(e)}")
            lomas_app.state.server_state["state"].append(DB_NOT_LOADED)
            lomas_app.state.server_state["message"].append(f"Admin database could not be loaded: {str(e)}")
            lomas_app.state.server_state["LIVE"] = False
            status_ok = False

        lomas_app.state.server_state["state"].append("Startup completed")
        lomas_app.state.server_state["message"].append("Startup completed")

    # Set DP Libraries config
    set_opendp_features_config(config.dp_libraries.opendp)

    if status_ok:
        logging.info("Server start condition OK")
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


# Initalise telemetry
resource = get_ressource(SERVER_SERVICE_NAME, SERVICE_ID)
init_telemetry(resource)

# This object holds the server object
app = FastAPI(lifespan=lifespan)

# Setting metrics middleware
app.add_middleware(FastAPIMetricMiddleware, app_name=SERVER_SERVICE_NAME)
app.add_middleware(LoggingAndTracingMiddleware)

# Add custom exception handlers
add_exception_handlers(app)

# Instrument the FastAPI app
FastAPIInstrumentor.instrument_app(app)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)
