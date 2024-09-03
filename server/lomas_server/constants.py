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
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"


# Query model input to DP librairy
MODEL_INPUT_TO_LIB = {
    "SmartnoiseSQLModel": DPLibraries.SMARTNOISE_SQL,
    "OpenDPModel": DPLibraries.OPENDP,
    "DiffPrivLibModel": DPLibraries.DIFFPRIVLIB,
}


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data"""

    PATH = "PATH_DB"
    S3 = "S3_DB"


# OpenDP Measurement Divergence Type
class OpenDPMeasurement(StrEnum):
    """Type of divergence for opendp measurement
    see https://docs.opendp.org/en/stable/api/python/opendp.measurements.html
    """

    FIXED_SMOOTHED_MAX_DIVERGENCE = "fixed_smoothed_max_divergence"
    MAX_DIVERGENCE = "max_divergence"
    SMOOTHED_MAX_DIVERGENCE = "smoothed_max_divergence"
    ZERO_CONCENTRATED_DIVERGENCE = "zero_concentrated_divergence"


# OpenDP Dataset Input Metric Type
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

# Smartnoise sql
STATS = ["count", "sum_int", "sum_large_int", "sum_float", "threshold"]
MAX_NAN_ITERATION = 5


# Data preprocessing
NUMERICAL_DTYPES = ["int16", "int32", "int64", "float16", "float32", "float64"]

# Example pipeline inputs
OPENDP_PIPELINE = (
    '{"version": "0.11", '
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

OPENDP_POLARS_PIPELINE = (
    '{"DataFrameScan":{"df":{"columns":[{"name":"region","datatype":"Int32",'
    '"bit_settings":"","values":[6,5,4,2,3,1,1,1,2,6]},{"name":"eco_branch",'
    '"datatype":"Int32","bit_settings":"","values":[66,90,55,63,94,73,65,59,'
    '60,92]},{"name":"profession","datatype":"Int32","bit_settings":"","values":'
    '[32,81,71,10,42,91,53,10,74,73]},{"name":"education","datatype":"Int32",'
    '"bit_settings":"","values":[7,2,1,7,1,5,1,3,4,4]},{"name":"age","datatype":'
    '"Int32","bit_settings":"","values":[36,19,18,23,18,49,42,48,30,46]},{"name":'
    '"sex","datatype":"Int32","bit_settings":"","values":[2,1,1,2,2,2,1,2,2,2]},'
    '{"name":"income","datatype":"Float64","bit_settings":"","values":[69156.22632'
    "652307,39503.22097393128,14374.55399721871,72427.3456792141,53010.07792509686,"
    "31713.94568033661,49097.70052434712,89059.29560055102,93470.30807966871,36421."
    '72447419795]}]},"schema":{"inner":{"region":"Int32","eco_branch":"Int32",'
    '"profession":"Int32","education":"Int32","age":"Int32","sex":"Int32","income":'
    '"Float64"}},"output_schema":null,"filter":null}}'
)

OPENDP_POLARS_PIPELINE_COVID = (
    '{"DataFrameScan":{"df":{"columns":[{"name":"patient_id","datatype":"Int32",'
    '"bit_settings":"","values":[7013,2739]},{"name":"id","datatype":"Int32",'
    '"bit_settings":"","values":[1023,540]},{"name":"date","datatype":"String",'
    '"bit_settings":"","values":["t","c"]},{"name":"temporal","datatype":"Int32",'
    '"bit_settings":"","values":[4,1]},{"name":"georegion","datatype":"String",'
    '"bit_settings":"","values":["BS","VS"]},{"name":"agegroup","datatype":"String",'
    '"bit_settings":"","values":["70 - 79","unknown"]},{"name":"sex","datatype":"String",'
    '"bit_settings":"","values":["other","other"]},{"name":"testType","datatype":"String",'
    '"bit_settings":"","values":["rapid_antigen_test","rapid_antigen_test"]},{"name":"testResult",'
    '"datatype":"String","bit_settings":"","values":["other","other"]},{"name":"country",'
    '"datatype":"String","bit_settings":"","values":["other","unknown"]},'
    '{"name":"subType","datatype":"String","bit_settings":"","values":["BA.2.75","XBB"]},'
    '{"name":"hospitalization","datatype":"Boolean","bit_settings":"",'
    '"values":[false,true]},{"name":"death","datatype":"Boolean","bit_settings":"",'
    '"values":[true,false]}]},"schema":{"inner":{"patient_id":"Int32","id":"Int32",'
    '"date":"String","temporal":"Int32","georegion":"String","agegroup":"String",'
    '"sex":"String","testType":"String","testResult":"String","country":"String",'
    '"subType":"String","hospitalization":"Boolean","death":"Boolean"}},'
    '"output_schema":null,"filter":null}}'
)