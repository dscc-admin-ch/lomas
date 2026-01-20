from enum import StrEnum

from opendp import measures as ms, typing as tp

# Server error messages
INTERNAL_SERVER_ERROR = "Internal server error. Please contact the administrator of this service."

TRACE_LOG_LEVEL = 5


class DPLibraries(StrEnum):
    """Name of DP Library used in the query."""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    OPENDP_POLARS = "opendp_polars"
    DIFFPRIVLIB = "diffprivlib"


# OpenDP
class OpenDpMechanism(StrEnum):
    """Name of OpenDP mechanisms."""

    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"


class OpenDpPipelineType(StrEnum):
    """Name of OpenDP pipelines."""

    LEGACY = "legacy"
    POLARS = "polars"


OPENDP_OUTPUT_MEASURE: dict[OpenDpMechanism, tp.Measure] = {
    OpenDpMechanism.LAPLACE: ms.max_divergence(),
    OpenDpMechanism.GAUSSIAN: ms.zero_concentrated_divergence(),
}


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


# Security
# ------------------------------------------------


class Scopes(StrEnum):
    """List of security scopes for the server endpoints."""

    ADMIN = "admin"
