import os
import string
from enum import StrEnum

# Get config and secrets from correct location
if "LOMAS_CONFIG_PATH" in os.environ:
    CONFIG_PATH = f"""{os.environ.get("LOMAS_CONFIG_PATH")}"""
    print(CONFIG_PATH)
else:
    CONFIG_PATH = "/usr/lomas_server/runtime.yaml"

if "LOMAS_SECRETS_PATH" in os.environ:
    SECRETS_PATH = f"""{os.environ.get("LOMAS_SECRETS_PATH")}"""
else:
    SECRETS_PATH = "/usr/lomas_server/secrets.yaml"


class ConfigKeys(StrEnum):
    """Keys of the configuration file"""

    RUNTIME_ARGS: str = "runtime_args"
    SERVER: str = "server"
    SETTINGS: str = "settings"
    DEVELOP_MODE: str = "develop_mode"
    TIME_ATTACK: str = "time_attack"
    SUBMIT_LIMIT: str = "submit_limit"
    DB: str = "admin_database"
    DB_TYPE: str = "db_type"
    DB_TYPE_MONGODB: str = "mongodb"
    MONGODB_ADDR: str = "address"
    MONGODB_PORT: str = "port"
    DATASET_STORE: str = "dataset_store"
    DATASET_STORE_TYPE: str = "ds_store_type"
    LRU_DATASET_STORE_MAX_SIZE: str = "max_memory_usage"
    DP_LIBRARY: str = "dp_libraries"


class AdminDBType(StrEnum):
    """Types of administration databases"""

    YAML: str = "yaml"
    MONGODB: str = "mongodb"


class DatasetStoreType(StrEnum):
    """Types of classes to handle datasets in memory"""

    BASIC: str = "basic"
    LRU: str = "LRU_cache"


class TimeAttackMethod(StrEnum):
    """Possible methods against timing attacks"""

    JITTER = "jitter"
    STALL = "stall"


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
    """Name of DP Library used in the query"""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"


# Query model input to DP librairy
MODEL_INPUT_TO_LIB = {
    "SmartnoiseSQLModel": DPLibraries.SMARTNOISE_SQL,
    "SmartnoiseSynthModel": DPLibraries.SMARTNOISE_SYNTH,
    "OpenDPModel": DPLibraries.OPENDP,
    "DiffPrivLibModel": DPLibraries.DIFFPRIVLIB,
}


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data"""

    PATH = "PATH_DB"
    S3 = "S3_DB"


# Smartnoise sql
SSQL_STATS = ["count", "sum_int", "sum_large_int", "sum_float", "threshold"]
SSQL_MAX_ITERATION = 5


# Smartnoise synth
class SSynthSynthesizer(StrEnum):
    """Synthesizer models for smartnoise synth"""

    # Marginal Synthesizer
    AIM = "aim"
    MWEM = "mwem"
    MST = "mst"
    PAC_SYNTH = "pacsynth"

    # Neural Network Synthesizer
    DP_CTGAN = "dpctgan"
    PATE_CTGAN = "patectgan"
    PATE_GAN = "pategan"  # no documentation
    DP_GAN = "dpgan"  # no documentation


class SSynthTableTransStyle(StrEnum):
    """Transformer style for smartnoise synth"""

    GAN = "gan"
    CUBE = "cube"


class SSynthColumnType(StrEnum):
    """Type of columns for SmartnoiseSynth transformer pre-processing"""

    PRIVATE_ID = "private_id"
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"
    ORDINAL = "ordinal"
    DATETIME = "datetime"


class SSynthAnonColumnType(StrEnum):
    UUID = "uuid4"
    EMAIL = "email"
    SSN = "ssn"
    SEQUENCE = "sequence"


# OpenDP
class OpenDPMeasurement(StrEnum):
    """Type of divergence for opendp measurement
    see https://docs.opendp.org/en/stable/api/python/opendp.measurements.html
    """

    FIXED_SMOOTHED_MAX_DIVERGENCE = "fixed_smoothed_max_divergence"
    MAX_DIVERGENCE = "max_divergence"
    SMOOTHED_MAX_DIVERGENCE = "smoothed_max_divergence"
    ZERO_CONCENTRATED_DIVERGENCE = "zero_concentrated_divergence"


class OpenDPDatasetInputMetric(StrEnum):
    """Type of opendp input metric for datasets
    see https://docs.opendp.org/en/stable/api/python/opendp.metrics.html
    see https://github.com/opendp/opendp/blob/main/rust/src/metrics/mod.rs
    """

    SYMMETRIC_DISTANCE = "SymmetricDistance"
    INSERT_DELETE_DISTANCE = "InsertDeleteDistance"
    CHANGE_ONE_DISTANCE = "ChangeOneDistance"
    HAMMING_DISTANCE = "HammingDistance"

    INT_DISTANCE = "u32"  # opendp type for distance between datasets


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


# Data preprocessing
NUMERICAL_DTYPES = ["int16", "int32", "int64", "float16", "float32", "float64"]

# Example pipeline inputs
OPENDP_PIPELINE = (
    '{"version": "0.10.0", '
    '"ast": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "partial_chain", "lhs": {'
    '"_type": "constructor", '
    '"func": "make_chain_tt", '
    '"module": "combinators", '
    '"args": ['
    "{"
    '"_type": "constructor", '
    '"func": "make_select_column", '
    '"module": "transformations", '
    '"kwargs": {"key": "bill_length_mm", "TOA": "String"}'
    "}, {"
    '"_type": "constructor", '
    '"func": "make_split_dataframe", '
    '"module": "transformations", '
    '"kwargs": {"separator": ",", "col_names": {"_type": '
    '"list", "_items": ["species", "island", '
    '"bill_length_mm", "bill_depth_mm", "flipper_length_'
    'mm", "body_mass_g", "sex"]}}'
    "}]}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_cast_default", '
    '"module": "transformations", '
    '"kwargs": {"TOA": "f64"}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_clamp", '
    '"module": "transformations", '
    '"kwargs": {"bounds": [30.0, 65.0]}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_resize", '
    '"module": "transformations", '
    '"kwargs": {"size": 346, "constant": 43.61}'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_variance", '
    '"module": "transformations"'
    "}}, "
    '"rhs": {'
    '"_type": "constructor", '
    '"func": "then_laplace", '
    '"module": "measurements", '
    '"kwargs": {"scale": 5.0}'
    "}}}"
)

DIFFPRIVLIB_PIPELINE = (
    '{"module": "diffprivlib", '
    '"version": "0.6.4", '
    '"pipeline": ['
    "{"
    '"type": "_dpl_type:StandardScaler", '
    '"name": "scaler", '
    '"params": {'
    '"with_mean": true, '
    '"with_std": true, '
    '"copy": true, '
    '"epsilon": 0.5, '
    '"bounds": {'
    '"_tuple": true, '
    '"_items": [[30.0, 13.0, 150.0, 2000.0], [65.0, 23.0, 250.0, 7000.0]]'
    "}, "
    '"random_state": null, '
    '"accountant": "_dpl_instance:BudgetAccountant"'
    "}"
    "}, "
    "{"
    '"type": "_dpl_type:LogisticRegression", '
    '"name": "classifier", '
    '"params": {'
    '"tol": 0.0001, '
    '"C": 1.0, '
    '"fit_intercept": true, '
    '"random_state": null, '
    '"max_iter": 100, '
    '"verbose": 0, '
    '"warm_start": false, '
    '"n_jobs": null, '
    '"epsilon": 1.0, '
    '"data_norm": 83.69469642643347, '
    '"accountant": "_dpl_instance:BudgetAccountant"'
    "}"
    "}"
    "]"
    "}"
)
