import logging
from collections.abc import Sequence
from enum import StrEnum
from importlib import metadata
from typing import Literal

import diffprivlib
from rich.logging import RichHandler

# Field names
# -----------------------------------------------------------------------------

DB_TYPE_FIELD = "database_type"
# TYPE_FIELD = "type"
# CARDINALITY_FIELD = "cardinality"

JSON_SCHEMA_EXAMPLES = "examples"


# Requests
# -----------------------------------------------------------------------------

DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

OPENDP_VERSION = metadata.version("opendp")
OpenDPFeatures = Sequence[Literal["contrib", "floating-point", "honest-but-curious"]]
DIFFPRIVLIB_VERSION = diffprivlib.__version__


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
    OIDC = "oidc"


# Logging
# -----------------------------------------------------------------------------


def init_logging(name: str = "root", level: str = "INFO") -> logging.Logger:
    # Set root logger config
    logging.basicConfig(
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
    )
    # Set level for current logger
    logging.getLogger(name).setLevel(level)

    for loggers in ["aio_pika", "aiormq", "botocore", "faker", "urllib3", "httpx"]:
        logging.getLogger(loggers).setLevel(logging.INFO)
    return logging.getLogger(name)


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
