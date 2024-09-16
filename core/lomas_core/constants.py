from enum import StrEnum

# Server error messages
INTERNAL_SERVER_ERROR = (
    "Internal server error. Please contact the administrator of this service."
)

class DPLibraries(StrEnum):
    """Name of DP Library used in the query"""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"