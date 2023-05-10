import pkg_resources
import traceback
from dp_queries.smartnoise_json.smartnoise_sql import (
    smartnoise_dataset_factory,
    SmartnoiseSQLQuerier,
)

from database.yaml_database import YamlDatabase
from utils.config import Config
from utils.constants import (
    CONFIG_NOT_LOADED,
    DATASET_NOT_LOADED,
    IRIS_DATASET,
    PENGUIN_DATASET,
    SERVER_LIVE,
    USER_DB_NOT_LOADED,
)
from utils.loggr import LOG

# Define global variables
IRIS_QUERIER: SmartnoiseSQLQuerier = None
PENGUIN_QUERIER: SmartnoiseSQLQuerier = None
CONFIG: Config = None
USER_DATABASE: YamlDatabase = None

# General server state, can add fields if need be.
SERVER_STATE: dict = {
    "state": ["NA"],
    "message": ["NA"],
    "LIVE": False,
}

OPENDP_VERSION = pkg_resources.get_distribution("opendp").version


def set_datasets_fromDB():
    global IRIS_QUERIER, PENGUIN_QUERIER
    try:
        IRIS_QUERIER = smartnoise_dataset_factory(IRIS_DATASET)
    except Exception as e:
        SERVER_STATE["state"].append("Failed while loading IRIS dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(
            400, f"Error reading iris dataset from provided  DB: {e}"
        )
    try:
        PENGUIN_QUERIER = smartnoise_dataset_factory(PENGUIN_DATASET)
    except Exception as e:
        SERVER_STATE["state"].append("Failed while loading PENGUIN dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(
            400, f"Error reading Penguin dataset from provided  DB: {e}"
        )


def check_start_condition():
    """
    This function checks the server started correctly and SERVER_STATE is
    updated accordingly.

    This has potential side effects on the return values of the "depends"
    functions, which check the server state.
    """
    if CONFIG is None:
        LOG.info("Config not loaded")
        SERVER_STATE["state"].append(CONFIG_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False

    if USER_DATABASE is None:
        LOG.info("User database not loaded")
        SERVER_STATE["state"].append(USER_DB_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False

    if IRIS_QUERIER is None:
        LOG.info("Smartnoise SQL IRIS Datasets not loaded")
        SERVER_STATE["state"].append(DATASET_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
    else:
        LOG.info("Smartnoise SQL IRIS Datasets successfully loaded")
        SERVER_STATE["state"].append(SERVER_LIVE)
        SERVER_STATE["message"].append("Server started!")
        SERVER_STATE["LIVE"] = True

    if PENGUIN_QUERIER is None:
        LOG.info("Smartnoise SQL PENGUIN Datasets not loaded")
        SERVER_STATE["state"].append(DATASET_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
    else:
        LOG.info("Smartnoise SQL PENGUIN Datasets successfully loaded")
        SERVER_STATE["state"].append(SERVER_LIVE)
        SERVER_STATE["message"].append("Server started!")
        SERVER_STATE["LIVE"] = True
