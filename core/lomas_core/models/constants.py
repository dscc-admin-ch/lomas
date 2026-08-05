import logging
from collections.abc import Sequence
from enum import StrEnum
from importlib import metadata
from typing import Literal

import diffprivlib
import httpx2
from rich.console import Console
from rich.logging import RichHandler

# Field names
# -----------------------------------------------------------------------------

DB_TYPE_FIELD = "database_type"
JSON_SCHEMA_EXAMPLES = "examples"


# Request / Responses
# -----------------------------------------------------------------------------

DUMMY_NB_ROWS = 100
DUMMY_SEED = 42

OPENDP_VERSION = metadata.version("opendp")
OpenDPFeatures = Sequence[Literal["contrib", "idealized-numerics", "honest-but-curious"]]
DIFFPRIVLIB_VERSION = diffprivlib.__version__


class QueryTypes(StrEnum):
    """Type of Lomas dataset query."""

    QUERY = "query"
    COST = "cost"
    DUMMY = "dummy"


class QueryResponseTypes(StrEnum):
    """Type of Lomas dataset query response."""

    COST = "cost"
    QUERY = "query"


class JobStatus(StrEnum):
    """Possible jobs status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    COMPLETE = "complete"


class LomasHeaders(StrEnum):
    APIKEY = "x-api-key"
    FORUSER = "x-for-user"
    WORKERUSER = "x-worker-api"


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


class FilterOutLiveSuccess:
    """Filter out INFO logs: GET /live HTTP/1.1 200 OK."""

    def filter(self, record: logging.LogRecord) -> bool:  # pylint: disable=missing-function-docstring
        match record.args:
            case (_, "GET", "/live", _, 200):
                return False
            case (_, "GET", str(full_path), _, 204):
                # handle worker prefix if any
                return "job/pending" not in full_path
            case ("GET", httpx2.URL() as url, _, 204, _):
                return "job/pending" not in url.path
            case _:
                return True


def init_logging(name: str, level: str = "INFO", lomas_level: str = "INFO") -> None:
    """Sets basic logging config to level and creates a logger named after name with log level lomas_level.

    This function is meant to set a parent logger for the lomas_* module with a different
    log level than the root logger.

    Args:
        name (str): Name of the parent logger to create
        level (str): Log level for the root logger.
        lomas_level (str): Log level for the parent logger.
    """
    console = Console(width=200, force_terminal=True)
    logging.basicConfig(
        format="%(message)s - %(name)s",
        datefmt="[%H:%M:%S]",
        handlers=[
            RichHandler(console=console, show_time=True, rich_tracebacks=False, tracebacks_show_locals=True)
        ],
        level=level,
    )
    logging.getLogger("httpx2").addFilter(FilterOutLiveSuccess())
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
    USER_NOT_FOUND = "UserNotFoundException"
    DATASET_NOT_FOUND = "DatasetNotFoundException"
    JOB_NOT_FOUND = "JobNotFoundException"
    EXTERNAL_LIBRARY = "ExternalLibraryException"
    UNAUTHORIZED_ACCESS = "UnauthorizedAccessException"
    INTERNAL_SERVER = "InternalServerException"
