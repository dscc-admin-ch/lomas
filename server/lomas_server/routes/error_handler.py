from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from lomas_core.exceptions import (
    DatasetNotFoundException,
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
    JobNotFoundException,
    LomasAPIException,
    UnauthorizedAccessException,
    UserNotFoundException,
)
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.exceptions import LomasAPIErrorModel

logger = get_lomas_logger(__name__)


# Custom exception handlers
def add_exception_handlers(app: FastAPI) -> None:
    """
    Translates custom exceptions to JSONResponses.

    Args:
        app (FastAPI): A fastapi App.
    """

    @app.exception_handler(LomasAPIException)
    async def lomas_exception_handler(_: Request, exc: LomasAPIException) -> JSONResponse:
        model, status_code = model_from_lomas_exception(exc)
        return JSONResponse(status_code=status_code, content=jsonable_encoder(model))


def model_from_lomas_exception(exc: Exception) -> tuple[LomasAPIErrorModel, int]:
    # Log exception
    if not isinstance(exc, LomasAPIException):
        logger.error(f"Unforseen exception occured: {exc}")
    else:
        logger.error(exc)

    # Attribute status code
    match exc:
        case UserNotFoundException() | DatasetNotFoundException() | JobNotFoundException():
            status_code = status.HTTP_404_NOT_FOUND
        case InternalServerException():
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        case ExternalLibraryException():
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        case InvalidQueryException():
            status_code = status.HTTP_400_BAD_REQUEST
        case UnauthorizedAccessException():
            status_code = status.HTTP_403_FORBIDDEN
        case _:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            # Hide source exception message from client.
            exc = InternalServerException("Unforseen exception occured.")

    model = LomasAPIErrorModel(message=str(exc))

    return (model, status_code)


# Server error responses for API queries (can only put one model per status code)
API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_400_BAD_REQUEST: {"model": LomasAPIErrorModel},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": LomasAPIErrorModel},
    status.HTTP_403_FORBIDDEN: {"model": LomasAPIErrorModel},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": LomasAPIErrorModel},
    status.HTTP_404_NOT_FOUND: {"model": LomasAPIErrorModel},
}
