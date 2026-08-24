from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from lomas_core.exceptions import InternalServerException
from lomas_core.models.constants import get_lomas_logger
from lomas_server.models.config import Config
from lomas_server.routes import routes_admin, routes_dp, routes_user, routes_worker
from lomas_server.routes.error_handler import add_exception_handlers
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.utils.notify import notify

logger = get_lomas_logger(__name__)


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
    lomas_app.state.config = config

    # Load admin database
    try:
        # Database
        logger.info("Loading admin database")
        lomas_app.state.admin_database = config.database

        # Auth/authz
        logger.info("Loading authenticator")
        lomas_app.state.authenticator = config.authenticator

        # Private db credentials
        lomas_app.state.private_db_credentials = config.private_db_credentials
    except InternalServerException as e:
        logger.exception(f"Failed at startup: {e!s}")

    notify(b"READY=1")
    try:
        yield  # lomas_app is handling requests
    finally:
        notify(b"STOPPING=1")


def get_user_app(config: Config) -> FastAPI:
    # This object holds the server object
    app = FastAPI(lifespan=lifespan)

    # Setting metrics middleware
    app.add_middleware(FastAPIMetricMiddleware, app_name=config.telemetry.service_name)
    app.add_middleware(LoggingAndTracingMiddleware)

    # Add custom exception handlers
    add_exception_handlers(app)

    # Instrument the FastAPI app
    FastAPIInstrumentor.instrument_app(app)

    # Add endpoints
    app.include_router(routes_dp.router)
    app.include_router(routes_user.router)

    return app


def get_admin_app(config: Config) -> FastAPI:
    # This object holds the server object
    app = FastAPI(lifespan=lifespan)

    # Setting metrics middleware
    app.add_middleware(FastAPIMetricMiddleware, app_name=config.telemetry.service_name)
    app.add_middleware(LoggingAndTracingMiddleware)

    # Add custom exception handlers
    add_exception_handlers(app)

    # Instrument the FastAPI app
    FastAPIInstrumentor.instrument_app(app)

    # Add endpoints
    app.include_router(routes_admin.router)
    app.include_router(routes_worker.router)

    return app
