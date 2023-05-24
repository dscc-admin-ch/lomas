# Configurations
CONFIG_PATH = "/usr/sdd_poc_server/runtime.yaml"
YAML_USER_DATABASE = "/usr/sdd_poc_server/user_database.yaml"
QUERIES_ARCHIVES = "/usr/sdd_poc_server/queries_archive.json"
MONGODB_CONTAINER_NAME = "mongodb"

# Configuration field names and values
CONF_RUNTIME_ARGS = "runtime_args"
CONF_SETTINGS = "settings"
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

DATASET_PATHS = {IRIS_DATASET: IRIS_DATASET_PATH, PENGUIN_DATASET: PENGUIN_DATASET_PATH}
DATASET_METADATA_PATHS = {IRIS_DATASET: IRIS_METADATA_PATH, PENGUIN_DATASET: PENGUIN_METADATA_PATH}
