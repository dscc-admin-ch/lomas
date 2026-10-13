from enum import StrEnum

# Server error messages
INTERNAL_SERVER_ERROR = "Internal server error. Please contact the administrator of this service."

TRACE_LOG_LEVEL = 5


class DPLibraries(StrEnum):
    """Name of DP Library used in the query."""

    SMARTNOISE_SQL = "smartnoise_sql"
    OPENDP = "opendp"
    OPENDP_POLARS = "opendp_polars"
    DIFFPRIVLIB = "diffprivlib"


# Security
# ------------------------------------------------


class Scopes(StrEnum):
    """List of security scopes for the server endpoints."""

    ADMIN = "admin"


OIDC_LOMAS_CLIENT__CLIENT_ID = "lomas_client"
