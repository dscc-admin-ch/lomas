from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from lomas_core.constants import DPLibraries
from lomas_core.models.constants import ExceptionType


class LomasServerExceptionModel(BaseModel):
    """Base model for lomas server exceptions."""

    model_config = ConfigDict(use_attribute_docstrings=True)
    type: str
    """Exception type."""


class InvalidQueryExceptionModel(LomasServerExceptionModel):
    """Exception directly related to the query.

    For example if it does not contain a DP mechanism or there is not enough DP budget.
    """

    type: Literal[ExceptionType.INVALID_QUERY] = ExceptionType.INVALID_QUERY
    """Exception type."""
    message: str
    """Exception error message.

    This is for exceptions directly related to the query.
    For example if it does not contain a DP mechanism or
    there is not enough DP budget.
    """
    # Note: we duplicate the class docstring to show it in the openapi doc.


class ExternalLibraryExceptionModel(LomasServerExceptionModel):
    """For exceptions from libraries external to the lomas packages."""

    type: Literal[ExceptionType.EXTERNAL_LIBRARY] = ExceptionType.EXTERNAL_LIBRARY
    """Exception type."""
    library: DPLibraries
    """The external library that caused the exception."""
    message: str
    """Exception error message.

    For exceptions from libraries external to the lomas packages.
    """


class UnauthorizedAccessExceptionModel(LomasServerExceptionModel):
    """Exception related to rights with regards to the query.

    (e.g. no user access for this dataset).
    """

    type: Literal[ExceptionType.UNAUTHORIZED_ACCESS] = ExceptionType.UNAUTHORIZED_ACCESS
    """Exception type."""
    message: str
    """Exception error message.

    Exception related to rights with regards to the query.
    (e.g. no user access for this dataset).
    """


class InternalServerExceptionModel(LomasServerExceptionModel):
    """For any unforseen internal exception."""

    type: Literal[ExceptionType.INTERNAL_SERVER] = ExceptionType.INTERNAL_SERVER
    """Exception type.

    For any unforseen internal exception.
    """


LomasServerExceptionTypeAdapter: TypeAdapter = TypeAdapter(
    Annotated[
        Union[
            InvalidQueryExceptionModel,
            ExternalLibraryExceptionModel,
            UnauthorizedAccessExceptionModel,
            InternalServerExceptionModel,
        ],
        Field(discriminator="type"),
    ]
)
