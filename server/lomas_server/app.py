import logging
import logging.config
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
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.config import Config
from lomas_server.admin_database.mongodb_database import AdminMongoDatabase
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.routes.utils import rabbitmq_ctx


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

    # Load Config
    config = Config()

    # Set some app state
    lomas_app.state.admin_database = None
    lomas_app.state.jobs_var = ContextVar("jobs", default={})
    lomas_app.state.private_credentials = config.private_db_credentials

    # Load admin database
    try:
        logging.info("Loading admin database")
        lomas_app.state.admin_database = AdminMongoDatabase(config.admin_database)
        logging.info("Loading authenticator")
        lomas_app.state.authenticator = config.authenticator.user_auth()

    except InternalServerException as e:
        logging.exception(f"Failed at startup: {e!s}")

    # Set DP Libraries config
    set_opendp_features_config(config.opendp_features)

    async with rabbitmq_ctx(lomas_app):
        yield  # lomas_app is handling requests


# Init config for logging purposes
initConfig = Config()
logging.config.dictConfig(initConfig.logging_config)

# Initalise telemetry
if initConfig.telemetry.enabled:
    LoggingInstrumentor().instrument(set_logging_format=True)
    init_telemetry(initConfig.telemetry)

# This object holds the server object
app = FastAPI(lifespan=lifespan)

# Setting metrics middleware
app.add_middleware(FastAPIMetricMiddleware, app_name=initConfig.telemetry.service_name)
app.add_middleware(LoggingAndTracingMiddleware)

# Add custom exception handlers
add_exception_handlers(app)

# Instrument the FastAPI app
FastAPIInstrumentor.instrument_app(app)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)
