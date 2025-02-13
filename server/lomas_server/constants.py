import os
import string
from enum import StrEnum

# Config
# -----------------------------------------------------------------------------

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

SERVER_SERVICE_NAME = os.getenv("SERVER_SERVICE_NAME", "lomas-server-app")
SERVICE_ID = os.getenv("HOSTNAME", "default-host")


# Misc
# -----------------------------------------------------------------------------

# Server states
DB_NOT_LOADED = "User database not loaded"
CONFIG_NOT_LOADED = "Config not loaded"
SERVER_LIVE = "LIVE"

# General values
SECONDS_IN_A_DAY = 60 * 60 * 24

# DP constants (max budget per user per dataset)
EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.01

# Dummy dataset generation
RANDOM_STRINGS = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)
NB_RANDOM_NONE = 5  # if nullable, how many random none to add

# Data preprocessing
NUMERICAL_DTYPES = ["int16", "int32", "int64", "float16", "float32", "float64"]


# DP Libraries
# -----------------------------------------------------------------------------

# Smartnoise sql
SSQL_STATS = ["count", "sum_int", "sum_large_int", "sum_float", "threshold"]
SSQL_MAX_ITERATION = 5


# Smartnoise synth
class SSynthTableTransStyle(StrEnum):
    """Transformer style for smartnoise synth."""

    GAN = "gan"  # for SSynthGanSynthesizer
    CUBE = "cube"  # for SSynthMarginalSynthesizer


class SSynthColumnType(StrEnum):
    """Type of columns for SmartnoiseSynth transformer pre-processing."""

    PRIVATE_ID = "private_id"
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"
    DATETIME = "datetime"


SSYNTH_PRIVATE_COLUMN = "uuid4"
SSYNTH_DEFAULT_BINS = 10
SSYNTH_MIN_ROWS_PATE_GAN = 1000


# OpenDP
class OpenDPMeasurement(StrEnum):
    """Type of divergence for opendp measurement.

    see https://docs.opendp.org/en/stable/api/python/opendp.measurements.html
    """

    FIXED_SMOOTHED_MAX_DIVERGENCE = "fixed_smoothed_max_divergence"
    MAX_DIVERGENCE = "max_divergence"
    SMOOTHED_MAX_DIVERGENCE = "smoothed_max_divergence"
    ZERO_CONCENTRATED_DIVERGENCE = "zero_concentrated_divergence"


class OpenDPDatasetInputMetric(StrEnum):
    """Type of opendp input metric for datasets.

    see https://docs.opendp.org/en/stable/api/python/opendp.metrics.html
    see https://github.com/opendp/opendp/blob/main/rust/src/metrics/mod.rs
    """

    SYMMETRIC_DISTANCE = "SymmetricDistance"
    INSERT_DELETE_DISTANCE = "InsertDeleteDistance"
    CHANGE_ONE_DISTANCE = "ChangeOneDistance"
    HAMMING_DISTANCE = "HammingDistance"

    INT_DISTANCE = "u32"  # opendp type for distance between datasets
