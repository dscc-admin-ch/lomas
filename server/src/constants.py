import os
import string
from enum import StrEnum

if os.environ.get("IN_CONTAINER", False):
    CONFIG_PATH = "/usr/lomas_server/runtime.yaml"
    SECRETS_PATH = "/usr/lomas_server/secrets.yaml"
else:
    CONFIG_PATH = "tests/test_configs/example_config.yaml"
    SECRETS_PATH = "tests/test_configs/example_secrets.yaml"

# Configuration field names and values
CONF_RUNTIME_ARGS: str = "runtime_args"
CONF_SERVER: str = "server"
CONF_SETTINGS: str = "settings"
CONF_DEV_MODE: str = "develop_mode"
CONF_TIME_ATTACK: str = "time_attack"
CONF_SUBMIT_LIMIT: str = "submit_limit"
CONF_DB: str = "admin_database"
CONF_DB_TYPE: str = "db_type"
CONF_DB_TYPE_MONGODB: str = "mongodb"
CONF_MONGODB_ADDR: str = "address"
CONF_MONGODB_PORT: str = "port"
CONF_DATASET_STORE: str = "dataset_store"
CONF_DATASET_STORE_TYPE: str = "ds_store_type"
CONF_LRU_DATASET_STORE__MAX_SIZE: str = "max_memory_usage"


class AdminDBType(StrEnum):
    YAML_TYPE: str = "yaml"
    MONGODB_TYPE: str = "mongodb"


class ConfDatasetStore(StrEnum):
    BASIC: str = "basic"
    LRU: str = "LRU_cache"


# Server states
QUERY_HANDLER_NOT_LOADED = "QueryHander not loaded"
DB_NOT_LOADED = "User database not loaded"
CONFIG_NOT_LOADED = "Config not loaded"
SERVER_LIVE = "LIVE"

# Server error messages
INTERNAL_SERVER_ERROR = (
    "Internal server error. Please contact the administrator of this service."
)

# DP constants
EPSILON_LIMIT: float = 5.0
DELTA_LIMIT: float = 0.0004


# Supported DP libraries
class DPLibraries(StrEnum):
    SMARTNOISE_SQL = "smartnoise_sql"
    OPENDP = "opendp"


# Private Databases
class PrivateDatabaseType(StrEnum):
    PATH = "PATH_DB"
    S3 = "S3_DB"


# OpenDP Measurement Divergence Type
class OpenDPMeasurement(StrEnum):
    FIXED_SMOOTHED_MAX_DIVERGENCE = "fixed_smoothed_max_divergence"
    MAX_DIVERGENCE = "max_divergence"
    SMOOTHED_MAX_DIVERGENCE = "smoothed_max_divergence"
    ZERO_CONCENTRATED_DIVERGENCE = "zero_concentrated_divergence"


# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42
DEFAULT_NUMERICAL_MIN = -10000
DEFAULT_NUMERICAL_MAX = 10000
RANDOM_STRINGS = list(
    string.ascii_lowercase + string.ascii_uppercase + string.digits
)
RANDOM_DATE_START = "01/01/2000"
RANDOM_DATE_RANGE = 50 * 365 * 24 * 60 * 60  # 50 years
NB_RANDOM_NONE = 5  # if nullable, how many random none to add

# Smartnoise sql
STATS = ["count", "sum_int", "sum_large_int", "sum_float", "threshold"]
MAX_NAN_ITERATION = 5
