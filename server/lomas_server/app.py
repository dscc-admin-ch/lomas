from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
            lomas_app.state.server_state["message"].append(
                "Adding demo data to MongoDB Admin"
            )
            add_demo_data_to_mongodb_admin()

    # Load admin database
    if status_ok:
        try:
            LOG.info("Loading admin database")
            lomas_app.state.server_state["message"].append("Loading admin database")
            lomas_app.state.admin_database = admin_database_factory(
                config.admin_database
            )
        except InternalServerException as e:
            LOG.exception(f"Failed at startup: {str(e)}")
            lomas_app.state.server_state["state"].append(DB_NOT_LOADED)
            lomas_app.state.server_state["message"].append(
                f"Admin database could not be loaded: {str(e)}"
            )
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


# This object holds the server object
app = FastAPI(lifespan=lifespan)

# Add custom exception handlers
add_exception_handlers(app)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)
