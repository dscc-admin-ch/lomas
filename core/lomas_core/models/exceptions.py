from typing import NoReturn

from fastapi import status
from pydantic import BaseModel, ConfigDict

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


class LomasAPIErrorModel(BaseModel):
    """Base model / Exception for lomas server exceptions."""

    model_config = ConfigDict(use_attribute_docstrings=True)
    """Exception type.

    Model for lomas server errors.
    """
    # Note: we duplicate the class docstring to show it in the openapi doc.

    message: str
    """Exception error message."""

    def raise_exception(self) -> NoReturn:
        raise LomasAPIException(self.message)


def model_from_lomas_exception(exc: Exception) -> tuple[LomasAPIErrorModel, int]:
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
