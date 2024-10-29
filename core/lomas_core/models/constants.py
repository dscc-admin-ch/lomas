from enum import IntEnum, StrEnum

# Field names
# -----------------------------------------------------------------------------

DB_TYPE_FIELD = "database_type"
TYPE_FIELD = "type"
CARDINALITY_FIELD = "cardinality"


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

    RUNTIME_ARGS: str = "runtime_args"
    SETTINGS: str = "settings"


class AdminDBType(StrEnum):
    """Types of administration databases."""

    YAML: str = "yaml"
    MONGODB: str = "mongodb"


class TimeAttackMethod(StrEnum):
    """Possible methods against timing attacks."""

    JITTER = "jitter"
    STALL = "stall"


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data."""

    PATH = "PATH_DB"
    S3 = "S3_DB"
