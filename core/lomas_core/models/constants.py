from collections.abc import Sequence
from enum import IntEnum, StrEnum
from importlib import metadata
from typing import Literal

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

OPENDP_VERSION = metadata.version("opendp")
OpenDPFeatures = Sequence[Literal["contrib", "floating-point", "honest-but-curious"]]
DIFFPRIVLIB_VERSION = metadata.version("diffprivlib")


# Metadata
# -----------------------------------------------------------------------------


class MetadataColumnType(StrEnum):
    """Column types for metadata."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    # These two are only used by pydantic to select the model to parse.
    # The pydantic models for the metadata columns never set their type to either one of these values.
    CAT_INT = "categorical_int"
    CAT_STRING = "categorical_string"


CATEGORICAL_TYPE_PREFIX = "categorical_"


class Precision(IntEnum):
    """Precision of integer and float data."""

    SINGLE = 32
    DOUBLE = 64


# Config / Dataset Connectors
# -----------------------------------------------------------------------------


class TimeAttackMethod(StrEnum):
    """Possible methods against timing attacks."""

    JITTER = "jitter"
    STALL = "stall"


# Private Databases
class PrivateDatabaseType(StrEnum):
    """Type of Private Database for the private data."""

    PATH = "PATH_DB"
    S3 = "S3_DB"


class AuthenticationType(StrEnum):
    """Type of Authenticator to identify users."""

    FREE_PASS = "free_pass"
    JWT = "jwt"


DefaultLoggingConf = {
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "aio_pika.exchange": {"level": "DEBUG"},
        "aiormq.channel": {"level": "INFO"},
        "aiormq.connection": {"level": "INFO"},
        "botocore": {"level": "INFO"},
        "botocore.endpoint": {"level": "DEBUG"},
        "faker": {"level": "WARN"},
        "pymongo.command": {"level": "INFO"},
        "pymongo.connection": {"level": "INFO"},
        "pymongo.serverSelection": {"level": "INFO"},
        "pymongo.topology": {"level": "INFO"},
        "urllib3": {"level": "INFO"},
    },
    "root": {"handlers": ["stdout"], "level": "DEBUG"},
    "version": 1,
}


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
