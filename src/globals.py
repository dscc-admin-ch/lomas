from fastapi import UploadFile, HTTPException
from helpers.leaderboard import LeaderBoard
from smartnoise_json.stats import DPStats
import pandas as pd 
import traceback 
import pkg_resources

from mongodb import db
from loggr import LOG

# Global Objects
LEADERBOARD: LeaderBoard = None
QUERIER: DPStats = None
TRAIN: pd.DataFrame = None
TEST: pd.DataFrame = None
TRAIN_X: pd.DataFrame = None
TRAIN_Y: pd.DataFrame = None
TEST_X: pd.DataFrame = None
TEST_Y: pd.DataFrame = None
SERVER_STATE: dict = {"state": ["NA"], "message": ["NA"], "live": False}
LIVE: bool = False

EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.0004

OPENDP_VERSION = pkg_resources.get_distribution("opendp").version


def set_datasets_fromDB():
    global TRAIN, TEST, TRAIN_X, TRAIN_Y, TEST_X, TEST_Y, SERVER_STATE
    try: 
        train_full = pd.DataFrame(list(db.train_full.find({}, {"_id":0})))
        if "id" not in train_full.columns.values:
            raise Exception("id must be a column in the csv file uploaded.")
        if train_full["id"].is_unique:
            train_full.set_index("id", inplace=True)
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Train full dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading train_full dataset from provided  DB: {e}")
    try:
        test_full = pd.DataFrame(list(db.test_full.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Train full dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading train_full dataset from provided  DB: {e}")
    
    try:
        train_x = pd.DataFrame(list(db.train_x.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Train_x dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading train_x dataset from provided  DB: {e}")
    
    try:
        train_y = pd.DataFrame(list(db.train_y.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Train_y dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading train_y dataset from provided  DB: {e}")

    try:
        test_x = pd.DataFrame(list(db.test_x.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Test_X dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading test_x dataset from provided  DB: {e}")
    
    try:
        test_y = pd.DataFrame(list(db.test_y.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"].append("Failed while loading Test_Y dataset")
        SERVER_STATE["message"].append(str(traceback.format_exc()))
        raise ValueError(400, f"Error reading test_y dataset from provided  DB: {e}")

    TRAIN = train_full
    TEST = test_full
    TRAIN_X = train_x
    TRAIN_Y = train_y
    TEST_X = test_x
    TEST_Y = test_y

    LOG.info("Checking startup condition")
    check_start_condition()


def check_start_condition():
    global TEST, TRAIN, LEADERBOARD, LIVE, QUERIER
    if TEST is not None:
        if TRAIN is not None:
            LOG.info("Checking leaderboard for competition start")
            if LEADERBOARD is not None:
                LIVE = True
                SERVER_STATE["state"].append("LIVE")
                SERVER_STATE["message"].append("Competition Started")
                SERVER_STATE["live"] = LIVE
                QUERIER = DPStats(TRAIN)
                LOG.info("Competition started")
            else:
                # SERVER_STATE["state"].append("Leaderboard is None")
                # SERVER_STATE["message"].append(str(LEADERBOARD))
                LIVE = True
                SERVER_STATE["state"].append("LIVE")
                SERVER_STATE["message"].append("Competition Started")
                SERVER_STATE["live"] = LIVE
                QUERIER = DPStats(TRAIN)
                LOG.info("Competition started")
        else:
            SERVER_STATE["state"].append("TRAIN value is None")
            SERVER_STATE["message"].append("Competition not started!")
            SERVER_STATE["live"] = LIVE

    else:
        SERVER_STATE["state"].append("TEST value is None")
        SERVER_STATE["message"].append("Competition not started!")
        SERVER_STATE["live"] = LIVE