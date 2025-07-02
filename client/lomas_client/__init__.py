import logging
from logging import NullHandler

from .client import Client

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

__all__ = ("Client",)
