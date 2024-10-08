from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response

from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import add_demo_data_to_mongodb_admin
from lomas_server.constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    SERVER_LIVE,
    AdminDBType,
)
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.utils.anti_timing_att import anti_timing_att
from lomas_server.utils.config import get_config
from lomas_server.utils.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_server.utils.logger import LOG


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> (
    AsyncGenerator
):  # pylint: disable=redefined-outer-name, too-many-statements
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
    app.state.admin_database = None

    # General server state, can add fields if need be.
    app.state.server_state = {
        "state": [],
        "message": [],
        "LIVE": False,
    }
    app.state.server_state["state"].append("Startup event")

    status_ok = True
    # Load config
    try:
        LOG.info("Loading config")
        app.state.server_state["message"].append("Loading config")
        config = get_config()
        app.state.private_credentials = config.private_db_credentials
    except InternalServerException:
        LOG.info("Config could not loaded")
        app.state.server_state["state"].append(CONFIG_NOT_LOADED)
        app.state.server_state["message"].append(
            "Server could not be started!"
        )
        app.state.server_state["LIVE"] = False
        status_ok = False

    # Fill up user database if in develop mode ONLY
    if status_ok and config.develop_mode:
        LOG.info("!! Develop mode ON !!")
        app.state.server_state["message"].append("!! Develop mode ON !!")
        if config.admin_database.db_type == AdminDBType.MONGODB:
            LOG.info("Adding demo data to MongoDB Admin")
            app.state.server_state["message"].append(
                "Adding demo data to MongoDB Admin"
            )
            add_demo_data_to_mongodb_admin()

    # Load admin database
    if status_ok:
        try:
            LOG.info("Loading admin database")
            app.state.server_state["message"].append("Loading admin database")
            app.state.admin_database = admin_database_factory(
                config.admin_database
            )
        except InternalServerException as e:
            LOG.exception(f"Failed at startup: {str(e)}")
            app.state.server_state["state"].append(DB_NOT_LOADED)
            app.state.server_state["message"].append(
                f"Admin database could not be loaded: {str(e)}"
            )
            app.state.server_state["LIVE"] = False
            status_ok = False

        app.state.server_state["state"].append("Startup completed")
        app.state.server_state["message"].append("Startup completed")

    # Set DP Libraries config
    set_opendp_features_config(config.dp_libraries.opendp)

    if status_ok:
        LOG.info("Server start condition OK")
        app.state.server_state["state"].append(SERVER_LIVE)
        app.state.server_state["message"].append("Server start condition OK")
        app.state.server_state["LIVE"] = True

    yield  # app is handling requests

    # Shutdown event
    if (
        config is not None
        and app.state.admin_database is not None
        and config.admin_database.db_type == AdminDBType.YAML
    ):
        app.state.admin_database.save_current_database()


# This object holds the server object
app = FastAPI(lifespan=lifespan)


# A simple hack to hinder the timing attackers
@app.middleware("http")
async def middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """Adds delays to requests response to protect against timing attack"""
    return await anti_timing_att(request, call_next, get_config())


# Add custom exception handlers
add_exception_handlers(app)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)
