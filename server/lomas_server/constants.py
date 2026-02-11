import string
from enum import StrEnum

# Misc
# -----------------------------------------------------------------------------

# DP constants (max budget per user per dataset)
EPSILON_LIMIT: float = 10.0
DELTA_LIMIT: float = 0.01

# Dummy dataset generation
RANDOM_STRINGS = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)

# Data preprocessing
NUMERICAL_DTYPES = ["int16", "int32", "int64", "float16", "float32", "float64"]


class OIDCClaims(StrEnum):
    """OIDC claim names, also used as claim names in JWT token."""

    USER_NAME = "name"
    USER_EMAIL = "email"


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
