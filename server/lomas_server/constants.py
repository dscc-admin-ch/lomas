import os
import string
from enum import StrEnum

from opendp import measures as ms
from opendp import typing as tp

from lomas_core.constants import OpenDpMechanism

# Config
# -----------------------------------------------------------------------------

# Get config and secrets from correct location
CONFIG_PATH = os.getenv("LOMAS_CONFIG_PATH", "/usr/lomas_server/runtime.yaml")
SECRETS_PATH = os.getenv("LOMAS_SECRETS_PATH", "/usr/lomas_server/secrets.yaml")

SERVER_SERVICE_NAME = os.getenv("SERVER_SERVICE_NAME", "lomas-server-app")
SERVICE_ID = os.getenv("HOSTNAME", "default-host")
TELEMETRY = bool(os.getenv("LOMAS_TELEMETRY", ""))


# Misc
# -----------------------------------------------------------------------------

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


OPENDP_TYPE_MAPPING = {
    "int32": tp.i32,
    "float32": tp.f32,
    "int64": tp.i64,
    "float64": tp.f64,
    "string": tp.String,
    "boolean": bool,
}

OPENDP_OUTPUT_MEASURE: dict[OpenDpMechanism, tp.Measure] = {
    OpenDpMechanism.LAPLACE: ms.max_divergence(),
    OpenDpMechanism.GAUSSIAN: ms.zero_concentrated_divergence(),
}
