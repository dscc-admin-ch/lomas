from json import JSONDecodeError
from typing import Any, NoReturn, TypeVar

import requests
from fastapi import status
from pydantic import ValidationError

from lomas_client.http_client import LomasHttpClient
from lomas_core.exceptions import InternalServerException
from lomas_core.models.exceptions import LomasAPIErrorModel
from lomas_core.models.responses import ResponseModel


def raise_error(response: requests.Response) -> NoReturn:
    """Raise error message based on the HTTP response.

    Args:
        response (requests.Response): The response object from an HTTP request.

    Raise:
        Server Error
    """
    try:
        LomasAPIErrorModel.model_validate_json(response.content.decode("utf8")).raise_exception()
    except (ValidationError, JSONDecodeError) as e:
        raise InternalServerException(f"Could not parse server error: {response.content}") from e
    # For mypy errors
    raise AssertionError("unreachable")


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


ResponseT = TypeVar("ResponseT", bound=ResponseModel)


def validate_model_response(
    client: LomasHttpClient, response: requests.Response, response_model: type[ResponseT]
) -> ResponseT:
    """Validate and process a HTTP response.

    Args:
        response (requests.Response): The response object from an HTTP request.

    Returns:
        response_model: Model for responses requests.
    """
    if response.status_code != status.HTTP_202_ACCEPTED:
        raise_error(response)

    job_uid = response.json()["uid"]
    job = client.wait_for_job(job_uid)
    if job.status == "failed":
        assert job.error is not None, f"job {job_uid} failed without error !"
        job.error.raise_exception()

    return response_model.model_validate(job.result)
