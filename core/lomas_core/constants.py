from enum import StrEnum

# Server error messages
INTERNAL_SERVER_ERROR = (
    "Internal server error. Please contact the administrator of this service."
)


class DPLibraries(StrEnum):
    """Name of DP Library used in the query."""

    SMARTNOISE_SQL = "smartnoise_sql"
    SMARTNOISE_SYNTH = "smartnoise_synth"
    OPENDP = "opendp"
    DIFFPRIVLIB = "diffprivlib"


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
