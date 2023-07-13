# Configurations
CONFIG_PATH = "/usr/sdd_poc_server/runtime.yaml"
YAML_USER_DATABASE = "/usr/sdd_poc_server/user_database.yaml"
QUERIES_ARCHIVES = "/usr/sdd_poc_server/queries_archive.json"
MONGODB_CONTAINER_NAME = "mongodb"

# Configuration field names and values
CONF_RUNTIME_ARGS = "runtime_args"
CONF_SETTINGS = "settings"
CONF_DEV_MODE = "develop_mode"
CONF_TIME_ATTACK = "time_attack"
CONF_SUBMIT_LIMIT = "submit_limit"
CONF_DB = "database"
CONF_DB_TYPE = "db_type"
CONF_DB_TYPE_MONGODB = "mongodb"
CONF_DB_TYPE_YAML = "yaml"
CONF_YAML_DB = "db_file"
CONF_MONGODB_ADDR = "address"
CONF_MONGODB_PORT = "port"

# Server states
QUERY_HANDLER_NOT_LOADED = "QueryHander not loaded"
DB_NOT_LOADED = "Database not loaded"
CONFIG_NOT_LOADED = "Config not loaded"
SERVER_LIVE = "LIVE"


# Server error messages
INTERNAL_SERVER_ERROR = (
    "Internal server error. Please contact the administrator of this service."
)

# DP constants
EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.0004
EPSILON_INITIAL: float = 0.0
DELTA_INITIAL: float = 0.0

# Supported DP libraries
LIB_SMARTNOISE_SQL = "smartnoise_sql"
SUPPORTED_LIBS = [LIB_SMARTNOISE_SQL]
# Datasets
IRIS_DATASET = "IRIS"
IRIS_DATASET_PATH = (
    "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
)
IRIS_METADATA_PATH = "metadata/iris_metadata.yaml"

PENGUIN_DATASET = "PENGUIN"
PENGUIN_DATASET_PATH = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv"
PENGUIN_METADATA_PATH = "metadata/penguin_metadata.yaml"

DATASET_PATHS = {
    IRIS_DATASET: IRIS_DATASET_PATH,
    PENGUIN_DATASET: PENGUIN_DATASET_PATH,
}
DATASET_METADATA_PATHS = {
    IRIS_DATASET: IRIS_METADATA_PATH,
    PENGUIN_DATASET: PENGUIN_METADATA_PATH,
}

EXISTING_DATASETS = [IRIS_DATASET, PENGUIN_DATASET]

# Dummy queries
DUMMY_EPSILON = 1e32 * 1.0
DUMMY_DELTA = 1.0

# Dummy dataset generation
DUMMY_NB_ROWS = 100
DUMMY_SEED = 42
SSQL_METADATA_OPTIONS = [
    "max_ids",
    "row_privacy",
    "sample_max_ids",
    "censor_dims",
    "clamp_counts",
    "clamp_columns",
    "use_dpsu",
]
DEFAULT_NUMERICAL_MIN = -10000
DEFAULT_NUMERICAL_MAX = 10000
RANDOM_STRINGS = ["a", "b", "c", "d"]
RANDOM_DATE_START = "01/01/2000"
RANDOM_DATE_RANGE = 50 * 365 * 24 * 60 * 60  # 50 years
NB_RANDOM_NONE = 5  # if nullable, how many random none to add


# MongoDB
MONGODB_CONTAINER_NAME = "mongodb"
MONGODB_PORT = "27017"
DATABASE_NAME = "user_database"
