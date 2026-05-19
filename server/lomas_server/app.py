from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import get_lomas_logger, init_logging
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.models.config import Config
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.routes.utils import rabbitmq_ctx


@asynccontextmanager
async def lifespan(lomas_app: FastAPI) -> AsyncGenerator[None]:
    """
    Lifespan function for the server.

    This function is executed once on server startup, yields and
    finishes running at server shutdown.

    Server initialization is performed (config loading, etc.) and
    the server state is updated accordingly. This can have potential
    side effects on the return values of the "depends"
    functions, which check the server state.
    """
    # Load Config
    config = Config()

    # Set some app state
    lomas_app.state.jobs = {}

    # Load admin database
    try:
        logger.info("Loading admin database")
        lomas_app.state.admin_database = config.database
        logger.info("Loading authenticator")
        lomas_app.state.authenticator = config.authenticator

        if not config.database.get_bootstrap_disabled():
            logger.info("Setting bootstrap credentials.")
            config.database.set_bootstrap(config.bootstrap)
        else:
            logger.warning("Not setting bootstrap credentials because already disabled in the admin database")
        lomas_app.state.bootstrap = config.bootstrap
        lomas_app.state.private_db_credentials = config.private_db_credentials
    except InternalServerException as e:
        logger.exception(f"Failed at startup: {e!s}")

    # Set DP Libraries config
    set_opendp_features_config(config.opendp_features)

    async with rabbitmq_ctx(lomas_app):
        yield  # lomas_app is handling requests


# Init config for logging purposes
initConfig = Config()

init_logging(
    name="lomas_server", level=initConfig.server.log_level, lomas_level=initConfig.server.lomas_log_level
)

logger = get_lomas_logger(__name__)


# Initalise telemetry
if initConfig.telemetry.enabled:
    LoggingInstrumentor().instrument(set_logging_format=True)
    AioPikaInstrumentor().instrument()

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
