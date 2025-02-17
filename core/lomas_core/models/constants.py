from enum import IntEnum, StrEnum

import pkg_resources

# Field names
# -----------------------------------------------------------------------------

DB_TYPE_FIELD = "database_type"
TYPE_FIELD = "type"
CARDINALITY_FIELD = "cardinality"

JSON_SCHEMA_EXAMPLES = "examples"


# Requests
# -----------------------------------------------------------------------------

DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

OPENDP_VERSION = pkg_resources.get_distribution("opendp").version
DIFFPRIVLIB_VERSION = pkg_resources.get_distribution("diffprivlib").version

# Metadata
# -----------------------------------------------------------------------------


class MetadataColumnType(StrEnum):
    """Column types for metadata."""

    STRING = "string"
    CAT_STRING = "categorical_string"
    INT = "int"
    CAT_INT = "categorical_int"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


CATEGORICAL_TYPE_PREFIX = "categorical_"


class Precision(IntEnum):
    """Precision of integer and float data."""

    SINGLE = 32
    DOUBLE = 64


# Config / Dataset Connectors
# -----------------------------------------------------------------------------


class ConfigKeys(StrEnum):
    """Keys of the configuration file."""

    RUNTIME_ARGS = "runtime_args"
    SETTINGS = "settings"


class AdminDBType(StrEnum):
    """Types of administration databases."""

    YAML = "yaml"
    MONGODB = "mongodb"


class TimeAttackMethod(StrEnum):
    """Possible methods against timing attacks."""

    JITTER = "jitter"
    STALL = "stall"


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data."""

    PATH = "PATH_DB"
    S3 = "S3_DB"


# Exceptions
# -----------------------------------------------------------------------------


class ExceptionType(StrEnum):
    """Lomas server exception types.

    To be used as discriminator when parsing corresponding models
    """

    INVALID_QUERY = "InvalidQueryException"
    EXTERNAL_LIBRARY = "ExternalLibraryException"
    UNAUTHORIZED_ACCESS = "UnauthorizedAccessException"
    INTERNAL_SERVER = "InternalServerException"
