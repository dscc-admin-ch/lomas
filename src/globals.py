from typing import Callable
from fastapi import UploadFile, HTTPException
from helpers.leaderboard import LeaderBoard
from smartnoise_json.stats import DPStats
import pandas as pd 
import traceback 

from mongodb import client
from loggr import LOG

# Global Objects
LEADERBOARD: LeaderBoard = None
QUERIER: DPStats = None
TRAIN: pd.DataFrame = None
TEST: pd.DataFrame = None
SERVER_STATE: dict = {"state": "NA", "message": "NA"}
LIVE: bool = False


def set_TRAIN(csv_file: UploadFile):
    global TRAIN

    try: 
        tmp_df = pd.read_csv(csv_file.file)
    except Exception as e:
        raise HTTPException(400, f"Error reading provided csv file: {e}")

    if "id" not in tmp_df.columns.values:
        raise HTTPException(400, f"id must be a column in the csv file uploaded.")
    
    if tmp_df["id"].is_unique:
        tmp_df.set_index("id", inplace=True)
    else:
        raise HTTPException(400, f"All values in the id column must be unique. This is important for the differential privacy budget.")

    if "labels" not in list(tmp_df.columns):
        raise HTTPException(400, f"There  must be a column named as 'labels' which contains the target values.")

    TRAIN = tmp_df



def set_TEST(csv_file: UploadFile):
    global TEST 
    
    try:
        tmp_df = pd.read_csv(csv_file.file)
    except Exception as e:
        raise HTTPException(400, f"Error reading provided csv file: {e}")

    if "id" not in tmp_df.columns.values:
        raise HTTPException(400, f"id must be a column in the csv file uploaded.")
    
    if tmp_df["id"].is_unique:
        tmp_df.set_index("id", inplace=True)
    else:
        raise HTTPException(400, f"All values in the id column must be unique. This is important for the differential privacy budget.")

    if "labels" not in list(tmp_df.columns):
        raise HTTPException(400, f"There  must be a column named as 'labels' which contains the target values.")

    TEST = tmp_df["labels"].to_frame().copy()

def set_datasets_fromDB():
    global TRAIN, TEST, SERVER_STATE
    try: 
        train_full = pd.DataFrame(list(client.datasets.train_full.find({}, {"_id":0})))
         
        if "id" not in train_full.columns.values:
            raise Exception("id must be a column in the csv file uploaded.")
        if train_full["id"].is_unique:
            train_full.set_index("id", inplace=True)
        else:
            raise Exception("All values in the id column must be unique. This is important for the differential privacy budget.")

        if "labels" not in list(train_full.columns):
            raise Exception(f"There  must be a column named as 'labels' which contains the target values.")

    except Exception as e: 
        SERVER_STATE["state"] = "Failed while loading Train full dataset"
        SERVER_STATE["message"] = str(traceback.format_exc())
        raise ValueError(400, f"Error reading train_full dataset from provided  DB: {e}")
    try:
        test_full = pd.DataFrame(list(client.datasets.test_full.find({}, {"_id":0})))
    except Exception as e: 
        SERVER_STATE["state"] = "Failed while loading Train full dataset"
        SERVER_STATE["message"] = str(traceback.format_exc())
        raise ValueError(400, f"Error reading train_full dataset from provided  DB: {e}")
    
    TRAIN = train_full
    TEST = test_full
    check_start_condition()


def check_start_condition():
    global TEST, TRAIN, LEADERBOARD, LIVE, QUERIER
    
    if TEST is not None:
        if TRAIN is not None:
            if LEADERBOARD is not None:
                LIVE = True
                SERVER_STATE["state"] = "LIVE"
                SERVER_STATE["message"] = "Competition Started"
                QUERIER = DPStats(TRAIN)
                LOG.info("Competition started")
