import warnings
from typing import Any

import requests
from fastapi import status
from lomas_core.constants import SSynthGanSynthesizer, SSynthMarginalSynthesizer
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
)


def raise_error(response: requests.Response) -> str:
    """Raise error message based on the HTTP response.

    Args:
        res (requests.Response): The response object from an HTTP request.

    Raise:
        Server Error
    """
    error_message = response.json()
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        raise InvalidQueryException(error_message["InvalidQueryException"])
    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        raise ExternalLibraryException(
            error_message["library"], error_message["ExternalLibraryException"]
        )
    if response.status_code == status.HTTP_403_FORBIDDEN:
        raise UnauthorizedAccessException(error_message["UnauthorizedAccessException"])
    if response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        raise InternalServerException(error_message["InternalServerException"])
    raise InternalServerException(f"Unknown {InternalServerException}")


def validate_synthesizer(synth_name: str, return_model: bool = False):
    """Validate smartnoise synthesizer (some model are not accepted).

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


def validate_model_response(response: requests.Response, response_model: Any) -> Any:
    """Validate and process a HTTP response.

    Args:
        response (requests.Response): The response object from an HTTP request.

    Returns:
        response_model: Model for responses requests.
    """
    if response.status_code == status.HTTP_200_OK:
        data = response.content.decode("utf8")
        r_model = response_model.model_validate_json(data)
        return r_model

    raise_error(response)
    return None
