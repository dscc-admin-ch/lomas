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


def init_logging(name: str, level: str = "INFO", lomas_level: str = "INFO") -> None:
    """Sets basic logging config to level and creates a logger named after name with log level lomas_level.

    This function is meant to set a parent logger for the lomas_* module with a different
    log level than the root logger.

    Args:
        name (str): Name of the parent logger to create
        level (str): Log level for the root logger.
        lomas_level (str): Log level for the parent logger.
    """
    logging.basicConfig(
        format="%(message)s %(name)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
        level=level,
    )

    logging.getLogger(name).setLevel(lomas_level)


def get_lomas_logger(name: str, level: str = "NOTSET") -> logging.Logger:
    """Get a logger with set level.

    Default level is always unset (getLogger default is warning).

    Args:
        name (str): Name of the logger.
        level (str, optional): Logging level. Defaults to "NOTSET".

    Returns:
        logging.Logger: Named logger with correct level.
    """
    logging.getLogger(name).setLevel(level)

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
