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

    # Order matters: registered first, checked last.
    @app.exception_handler(Exception)
    async def lomas_generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unforseen exception occured: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(InternalServerException()),
        )

    @app.exception_handler(LomasAPIException)
    async def lomas_api_exception_handler(_: Request, exc: LomasAPIException) -> JSONResponse:
        logger.exception(exc)
        return response_from_lomas_exception(exc)


def response_from_lomas_exception(exc: LomasAPIException) -> JSONResponse:
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

    model = LomasAPIErrorModel(message=str(exc))

    return JSONResponse(status_code=status_code, content=jsonable_encoder(model))


# Server error responses for API queries (can only put one model per status code)
API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_400_BAD_REQUEST: {"model": LomasAPIErrorModel},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": LomasAPIErrorModel},
    status.HTTP_403_FORBIDDEN: {"model": LomasAPIErrorModel},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": LomasAPIErrorModel},
    status.HTTP_404_NOT_FOUND: {"model": LomasAPIErrorModel},
}
