from enum import StrEnum

# Server error messages
INTERNAL_SERVER_ERROR = "Internal server error. Please contact the administrator of this service."

TRACE_LOG_LEVEL = 5


class DPLibraries(StrEnum):
    """Name of DP Library used in the query."""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    OPENDP_POLARS = "opendp_polars"
    OPENDP_SYNTH = "opendp_synth"
    DIFFPRIVLIB = "diffprivlib"


# OpenDP


# Smartnoise synth
class SSynthMarginalSynthesizer(StrEnum):
    """Marginal Synthesizer models for smartnoise synth."""

    AIM = "aim"
    MWEM = "mwem"
    MST = "mst"
    PAC_SYNTH = "pacsynth"


class SSynthGanSynthesizer(StrEnum):
    """GAN Synthesizer models for smartnoise synth."""

    DP_CTGAN = "dpctgan"
    PATE_CTGAN = "patectgan"
    PATE_GAN = "pategan"
    DP_GAN = "dpgan"


class OpenDPSynthAlgorithm(StrEnum):
    AIM = "aim"
    MST = "mst"
    FIXED = "fixed"


# Security
# ------------------------------------------------


class Scopes(StrEnum):
    """List of security scopes for the server endpoints."""

    ADMIN = "admin"


OIDC_LOMAS_CLIENT__CLIENT_ID = "lomas_client"
