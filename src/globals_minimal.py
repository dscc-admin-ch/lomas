from fastapi import UploadFile, HTTPException
from smartnoise_json.stats import DPStats
import pandas as pd 
import traceback 
import pkg_resources

from loggr import LOG

# Global Objects
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