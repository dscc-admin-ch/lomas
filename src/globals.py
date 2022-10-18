from typing import Callable
from fastapi import File, UploadFile, HTTPException
from helpers.leaderboard import LeaderBoard
from smartnoise_json.stats import DPStats
import pandas as pd 

# Global Objects
LEADERBOARD: LeaderBoard = None
QUERIER: DPStats = None
TRAIN: pd.DataFrame = None
TEST: pd.DataFrame = None
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


def check_start_condition():
    global TEST, TRAIN, LEADERBOARD, LIVE, QUERIER

    if TEST is not None:
        if TRAIN is not None:
            if LEADERBOARD is not None:
                LIVE = True
                QUERIER = DPStats(TRAIN)
