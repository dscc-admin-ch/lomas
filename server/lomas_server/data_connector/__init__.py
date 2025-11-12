from typing import Annotated

from pydantic import Field, TypeAdapter

from .data_connector import DataConnector
from .in_memory_connector import InMemoryConnector
from .path_connector import PathConnector
from .s3_connector import S3Connector

ConnectorUnion = Annotated[PathConnector | S3Connector | InMemoryConnector, Field(discriminator="type")]
ConnectorUnionTA: TypeAdapter = TypeAdapter(ConnectorUnion)

__all__ = ["ConnectorUnionTA", "DataConnector", "InMemoryConnector", "PathConnector", "S3Connector"]
