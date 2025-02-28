import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_core.instrumentation import get_ressource, init_telemetry
from lomas_core.models.constants import AdminDBType
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import add_demo_data_to_mongodb_admin
from lomas_server.constants import SERVER_SERVICE_NAME, SERVICE_ID, TELEMETRY
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.routes.utils import rabbitmq_ctx
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
    logging.info("Startup message")

    # Set some app state
    lomas_app.state.admin_database = None
    lomas_app.state.jobs_var = ContextVar("jobs", default={})

    # Load config
    try:
        logging.info("Loading config")
        config = get_config()
        lomas_app.state.private_credentials = config.private_db_credentials
    except InternalServerException:
        logging.info("Config could not loaded")

    # Fill up user database if in develop mode ONLY
    if config.develop_mode:
        logging.info("!! Develop mode ON !!")
        if config.admin_database.db_type == AdminDBType.MONGODB:
            logging.info("Adding demo data to MongoDB Admin")
            add_demo_data_to_mongodb_admin()

    # Load admin database
    try:
        logging.info("Loading admin database")
        lomas_app.state.admin_database = admin_database_factory(config.admin_database)
    except InternalServerException as e:
        logging.exception(f"Failed at startup: {str(e)}")

    # Set DP Libraries config
    set_opendp_features_config(config.dp_libraries.opendp)

    async with rabbitmq_ctx(lomas_app):

        yield  # lomas_app is handling requests


# Initalise telemetry
if TELEMETRY:
    LoggingInstrumentor().instrument(set_logging_format=True)
    init_telemetry(get_ressource(SERVER_SERVICE_NAME, SERVICE_ID))

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
