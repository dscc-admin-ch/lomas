import pandas as pd
import pkg_resources
from smartnoise_json.stats import smartnoise_dataset_factory, SmartnoiseSQLQuerier

from database.yaml_database import YamlDatabase
from utils.config import Config
from utils.constants import (
    DATASET_NOT_LOADED,
    SERVER_LIVE,
    USER_DB_NOT_LOADED
)
from utils.loggr import LOG

# Global Objects
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
        IRIS_QUERIER = smartnoise_dataset_factory('Iris')
    except Exception as e:
        SERVER_STATE["state"].append("Failed while loading Iris dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(
            400, f"Error reading iris dataset from provided  DB: {e}"
        )
    try:
        PENGUIN_QUERIER = smartnoise_dataset_factory('Penguin')
    except Exception as e:
        SERVER_STATE["state"].append("Failed while loading Penguin dataset")
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
    global SERVER_STATE, IRIS_QUERIER, PENGUIN_QUERIER, USER_DATABASE
    if USER_DATABASE is None:
        LOG.info("User database not loaded")
        SERVER_STATE["state"].append(USER_DB_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False

    if IRIS_QUERIER is None or PENGUIN_QUERIER is None:
        LOG.info("Dataset not loaded")
        SERVER_STATE["state"].append(DATASET_NOT_LOADED)
        SERVER_STATE["message"].append("Server could not be started!")
        SERVER_STATE["LIVE"] = False
    else:
        LOG.info("Dataset successfully  loaded")
        SERVER_STATE["state"].append(SERVER_LIVE)
        SERVER_STATE["message"].append("Server started!")
        SERVER_STATE["LIVE"] = True
