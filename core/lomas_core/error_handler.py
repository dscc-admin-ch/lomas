import logging
from typing import Any, Type

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pymongo.errors import WriteConcernError

from lomas_core.constants import DPLibraries
from lomas_core.models.exceptions import (
    ExternalLibraryExceptionModel,
    InternalServerExceptionModel,
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)


class InvalidQueryException(Exception):
    """
    Custom exception for invalid queries.

    For example, this exception will occur when the query:
        - is not an opendp measurement
        - cannot be reconstructed properly (for opendp and diffprivlib)
    """

    def __init__(self, error_message: str) -> None:
        """Invalid Query Exception initialisation.

        Args:
            error_message (str): _description_
        """
        self.error_message = error_message


class ExternalLibraryException(Exception):
    """
    Custom exception for issues within external libraries.

    This exception will occur when the processes fail within the
    external libraries (smartnoise-sql, opendp, diffprivlib)
    """

    def __init__(self, library: DPLibraries, error_message: str) -> None:
        """External Query Exception initialisation.

        Args:
            library (str): _description_
            error_message (str): _description_
        """
        self.library = library
        self.error_message = error_message


class UnauthorizedAccessException(Exception):
    """
    Custom exception for unauthorized access:

    (unknown user, no access to dataset, etc)
    """

    def __init__(self, error_message: str) -> None:
        self.error_message = error_message


class InternalServerException(Exception):
    """Custom exception for issues within server internal functionalities."""

    def __init__(self, error_message: str) -> None:
        self.error_message = error_message


KNOWN_EXCEPTIONS: tuple[Type[BaseException], ...] = (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
    WriteConcernError,
)


# Custom exception handlers
def add_exception_handlers(app: FastAPI) -> None:
    """
    Translates custom exceptions to JSONResponses.

    Args:
        app (FastAPI): A fastapi App.
    """

    @app.exception_handler(InvalidQueryException)
    async def invalid_query_exception_handler(_: Request, exc: InvalidQueryException) -> JSONResponse:
        logging.info(f"InvalidQueryException raised: {exc.error_message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(InvalidQueryExceptionModel(message=exc.error_message)),
        )

    @app.exception_handler(ExternalLibraryException)
    async def external_library_exception_handler(_: Request, exc: ExternalLibraryException) -> JSONResponse:
        logging.info(f"ExternalLibraryException raised: {exc.error_message}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                ExternalLibraryExceptionModel(message=exc.error_message, library=exc.library)
            ),
        )

    @app.exception_handler(UnauthorizedAccessException)
    async def unauthorized_access_exception_handler(
        _: Request, exc: UnauthorizedAccessException
    ) -> JSONResponse:
        logging.info(f"UnauthorizedAccessException raised: {exc.error_message}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=jsonable_encoder(UnauthorizedAccessExceptionModel(message=exc.error_message)),
        )

    @app.exception_handler(InternalServerException)
    async def internal_server_exception_handler(_: Request, exc: InternalServerException) -> JSONResponse:
        logging.info(f"InternalServerException  raised: {exc.error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(InternalServerExceptionModel()),
        )


# Server error responses for DP queries
SERVER_QUERY_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_400_BAD_REQUEST: {"model": InvalidQueryExceptionModel},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ExternalLibraryExceptionModel},
    status.HTTP_403_FORBIDDEN: {"model": UnauthorizedAccessExceptionModel},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": InternalServerExceptionModel},
}
