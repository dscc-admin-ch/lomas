from typing import NoReturn

from pydantic import BaseModel, ConfigDict

from lomas_core.exceptions import LomasAPIException


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
