# DP constants
EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.0004

# Configurations
CONFIG_PATH = "/usr/sdd_poc_server/runtime.yaml"
YAML_USER_DATABASE = "/usr/sdd_poc_server/user_database.yaml"
QUERIES_ARCHIVES = "/usr/sdd_poc_server/queries_archive.json"

# Server states
DATASET_NOT_LOADED = "Dataset(s) not loaded"
USER_DB_NOT_LOADED = "User database not loaded"
CONFIG_NOT_LOADED = "Config not loaded"
SERVER_LIVE = "LIVE"


# Datasets
IRIS_DATASET = "IRIS"
IRIS_DATASET_PATH = (
    "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
)
IRIS_METADATA_PATH = "metadata/iris_metadata.yaml"

PENGUIN_DATASET = "PENGUIN"
PENGUIN_DATASET_PATH = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv"
PENGUIN_METADATA_PATH = "metadata/penguin_metadata.yaml"
