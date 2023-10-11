import pkg_resources
from dp_queries.dp_logic import QueryHandler

from admin_database.admin_database import AdminDatabase
from utils.config import Config
from constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    QUERY_HANDLER_NOT_LOADED,
    SERVER_LIVE,
)
from utils.loggr import LOG

# Define global variables
CONFIG: Config = None
ADMIN_DATABASE: AdminDatabase = None
QUERY_HANDLER: QueryHandler = None

# General server state, can add fields if need be.
SERVER_STATE: dict = {
    "state": [],
    "message": [],
    "LIVE": False,
}

def check_start_condition():
    """
    This function checks the server started correctly and SERVER_STATE is
    updated accordingly.

    This has potential side effects on the return values of the "depends"
    functions, which check the server state.
    """
    status_ok = True
    if CONFIG is None:
        LOG.info("Config not loaded")
        SERVER_STATE["state"].append(CONFIG_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
        status_ok = False

    if ADMIN_DATABASE is None:
        LOG.info("Admin database not loaded")
        SERVER_STATE["state"].append(DB_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
        status_ok = False

    if QUERY_HANDLER is None:
        LOG.info("QueryHandler not loaded")
        SERVER_STATE["state"].append(QUERY_HANDLER_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
        status_ok = False

    if status_ok:
        LOG.info("Server start condition OK")
        SERVER_STATE["state"].append(SERVER_LIVE)
        SERVER_STATE["message"].append("Server start condition OK")
        SERVER_STATE["LIVE"] = True
