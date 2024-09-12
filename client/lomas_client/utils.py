import warnings
from enum import StrEnum


class SSynthMarginalSynthesizer(StrEnum):
    """Marginal Synthesizer models for smartnoise synth"""

    AIM = "aim"
    MWEM = "mwem"
    MST = "mst"
    PAC_SYNTH = "pacsynth"


class SSynthGanSynthesizer(StrEnum):
    """GAN Synthesizer models for smartnoise synth"""

    DP_CTGAN = "dpctgan"
    PATE_CTGAN = "patectgan"
    PATE_GAN = "pategan"
    DP_GAN = "dpgan"


def validate_synthesizer(synth_name: str, return_model: bool = False):
    """Validate smartnoise synthesizer (some model are not accepted)

    Args:
        synth_name (str): name of the Synthesizer model to use.
        return_model (bool): True to get Synthesizer model, False to get samples

    Raises:
        ValueError: if a synthesizer or its parameters are not valid
    """
    if synth_name in [
        SSynthGanSynthesizer.DP_CTGAN,
        SSynthGanSynthesizer.DP_GAN,
    ]:
        warnings.warn(
            f"Warning:{synth_name} synthesizer random generator for noise and "
            + "shuffling is not cryptographically secure. "
            + "(pseudo-rng in vanilla PyTorch)."
        )
    if synth_name == SSynthMarginalSynthesizer.MST and return_model:
        raise ValueError(
            f"{synth_name} synthesizer cannot be returned, only samples. "
            + "Please, change synthesizer or set `return_model=False`."
        )
    if synth_name == SSynthMarginalSynthesizer.PAC_SYNTH:
        raise ValueError(
            f"{synth_name} synthesizer not supported. "
            + "Please choose another synthesizer."
        )
