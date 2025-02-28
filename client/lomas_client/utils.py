import warnings
from typing import Any

import requests
from fastapi import status

from lomas_client.http_client import LomasHttpClient
from lomas_core.constants import SSynthGanSynthesizer, SSynthMarginalSynthesizer
from lomas_core.error_handler import raise_error_from_model
from lomas_core.models.exceptions import LomasServerExceptionTypeAdapter


def raise_error(response: requests.Response) -> None:
    """Raise error message based on the HTTP response.

    Args:
        res (requests.Response): The response object from an HTTP request.

    Raise:
        Server Error
    """
    error_model = LomasServerExceptionTypeAdapter.validate_json(response.json())
    raise_error_from_model(error_model)


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
        raise ValueError(f"{synth_name} synthesizer not supported. Please choose another synthesizer.")


def validate_model_response_direct(response: requests.Response, response_model: Any) -> Any:
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


def validate_model_response(client: LomasHttpClient, response: requests.Response, response_model: Any) -> Any:
    """Validate and process a HTTP response.

    Args:
        response (requests.Response): The response object from an HTTP request.

    Returns:
        response_model: Model for responses requests.
    """
    if response.status_code != status.HTTP_202_ACCEPTED:
        raise_error(response)
        return None

    job_uid = response.json()["uid"]
    job = client.wait_for_job(job_uid)
    if job.status == "failed":
        assert job.error is not None, "job {job_uid} failed without error !"
        raise_error_from_model(job.error)

    return response_model.model_validate(job.result)
