import os
import string
from enum import StrEnum

import pkg_resources

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
    DP_LIBRARY: str = "dp_libraries"


class AdminDBType(StrEnum):
    """Types of administration databases"""

    YAML: str = "yaml"
    MONGODB: str = "mongodb"


class TimeAttackMethod(StrEnum):
    """Possible methods against timing attacks"""

    JITTER = "jitter"
    STALL = "stall"


# Server states
DB_NOT_LOADED = "User database not loaded"
CONFIG_NOT_LOADED = "Config not loaded"
SERVER_LIVE = "LIVE"

# Server error messages
INTERNAL_SERVER_ERROR = (
    "Internal server error. Please contact the administrator of this service."
)

# General values
SECONDS_IN_A_DAY = 60 * 60 * 24

# DP constants (max budget per user per dataset)
EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.01


# Supported DP libraries
class DPLibraries(StrEnum):
    """Name of DP Library used in the query"""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data"""

    PATH = "PATH_DB"
    S3 = "S3_DB"


# Smartnoise sql
SSQL_STATS = ["count", "sum_int", "sum_large_int", "sum_float", "threshold"]
SSQL_MAX_ITERATION = 5


# Smartnoise synth
class SSynthMarginalSynthesizer(StrEnum):
    """Marginal Synthesizer models for smartnoise synth"""

    AIM = "aim"
    MWEM = "mwem"
    MST = "mst"
    PAC_SYNTH = "pacsynth"


class SSynthGanSynthesizer(StrEnum):
    """GAN Synthesizer models for smartnoise synth"""

    DP_CTGAN = "dpctgan"
    PATE_CTGAN = "patectgan"
    PATE_GAN = "pategan"
    DP_GAN = "dpgan"


class SSynthTableTransStyle(StrEnum):
    """Transformer style for smartnoise synth"""

    GAN = "gan"  # for SSynthGanSynthesizer
    CUBE = "cube"  # for SSynthMarginalSynthesizer


class SSynthColumnType(StrEnum):
    """Type of columns for SmartnoiseSynth transformer pre-processing"""

    PRIVATE_ID = "private_id"
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"
    DATETIME = "datetime"


SSYNTH_PRIVATE_COLUMN = "uuid4"
SSYNTH_DEFAULT_BINS = 10
SSYNTH_MIN_ROWS_PATE_GAN = 1000


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
RANDOM_STRINGS = list(
    string.ascii_lowercase + string.ascii_uppercase + string.digits
)
NB_RANDOM_NONE = 5  # if nullable, how many random none to add


# Data preprocessing
NUMERICAL_DTYPES = ["int16", "int32", "int64", "float16", "float32", "float64"]

# Example pipeline inputs
OPENDP_VERSION = pkg_resources.get_distribution("opendp").version
OPENDP_PIPELINE = (
    f'{{"version": "{OPENDP_VERSION}", '
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
