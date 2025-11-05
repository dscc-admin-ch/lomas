from json import JSONDecodeError
from typing import Any, Never, TypeVar

import requests
from fastapi import status
from pydantic import ValidationError

from lomas_client.http_client import LomasHttpClient
from lomas_core.error_handler import InternalServerException, raise_error_from_model
from lomas_core.models.exceptions import LomasServerExceptionTypeAdapter
from lomas_core.models.responses import ResponseModel


def raise_error(response: requests.Response) -> Never:
    """Raise error message based on the HTTP response.

    Args:
        res (requests.Response): The response object from an HTTP request.

    Raise:
        Server Error
    """
    try:
        error_model = LomasServerExceptionTypeAdapter.validate_python(response.json())
    except (ValidationError, JSONDecodeError) as e:
        raise InternalServerException(f"Could not parse server error: {response.content}") from e

    raise_error_from_model(error_model)


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
        raise_error_from_model(job.error)

    return response_model.model_validate(job.result)
