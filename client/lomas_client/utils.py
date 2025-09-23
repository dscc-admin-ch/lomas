import argparse
import inspect
import warnings
from collections.abc import Callable
from functools import wraps
from json import JSONDecodeError
from typing import TypeVar

import requests
from fastapi import status
from pydantic import ValidationError
from returns.functions import raise_exception
from returns.io import IOFailure, IOResultE, IOSuccess, impure_safe
from returns.unsafe import unsafe_perform_io

from lomas_client.http_client import LomasHttpClient
from lomas_core.constants import SSynthGanSynthesizer, SSynthMarginalSynthesizer
from lomas_core.error_handler import InternalServerException, specify_error_from_model
from lomas_core.models.exceptions import LomasServerExceptionType, LomasServerExceptionTypeAdapter
from lomas_core.models.responses import ResponseModel


def parse_if_ok(res: requests.Response) -> IOResultE[str]:
    """Only continues if Response is OK (200)."""
    if res.status_code == status.HTTP_200_OK:
        return IOSuccess(res.content.decode("utf8"))
    return parse_server_error(res).bind_result(specify_error_from_model)


def parse_server_error(response: requests.Response) -> IOResultE[LomasServerExceptionType]:
    """Parse a server error message based on the HTTP response.

    Args:
        res (requests.Response): The response object from an HTTP request.

    Return:
        ResultE[LomasServerExceptionType]
    """
    try:
        error_model = LomasServerExceptionTypeAdapter.validate_python(response.json())
        return IOSuccess(error_model)
    except (ValidationError, JSONDecodeError):
        return IOFailure(InternalServerException(f"Could not parse server error: {response.content}"))


@impure_safe
def validate_synthesizer(synth_name: str, return_model: bool = False) -> None:
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


ResponseT = TypeVar("ResponseT", bound=ResponseModel)


def validate_model_response(
    client: LomasHttpClient, response_model: type[ResponseT]
) -> Callable[[requests.Response], IOResultE[ResponseT]]:
    """Validate and process a HTTP response.

    Args:
        response (requests.Response): The response object from an HTTP request.

    Returns:
        response_model: Model for responses requests.
    """

    def validate(response: requests.Response) -> IOResultE[ResponseT]:
        if response.status_code != status.HTTP_202_ACCEPTED:
            return parse_server_error(response).bind_result(specify_error_from_model)

        job_uid = response.json()["uid"]
        job = client.wait_for_job(job_uid)
        if job.status == "failed":
            assert job.error is not None, f"job {job_uid} failed without error !"
            specify_error_from_model(job.error)

        return impure_safe(response_model.model_validate)(job.result)

    return validate


T = TypeVar("T")


def unwrap(result: T | IOResultE[T]) -> T:
    """Unwrap IOResultE[T] back to T in the unsafest way possible."""
    if not hasattr(result, "unwrap"):
        # Nothing to do
        return result

    # First raise the internal Exception if the container is a failure
    inner_success = result.alt(raise_exception).unwrap()  # type: ignore
    # Otherwise force-escape IO
    return unsafe_perform_io(inner_success)


def call_and_unwrap_wrapper(method: Callable) -> Callable:
    """Unwrap IOResultE[T] back to T in the unsafest way possible."""

    @wraps(method)
    def call_and_unwrap(*args: argparse.Namespace, **kwargs: dict) -> Callable:
        return unwrap(method(*args, **kwargs))

    return call_and_unwrap


def unwrap_all_clsmethods(cls: type) -> type:
    """Add a wrapper to all (public) methods of the given Class."""
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_"):
            setattr(cls, name, call_and_unwrap_wrapper(method))
    return cls
