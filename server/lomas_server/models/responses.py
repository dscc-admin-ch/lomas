from pydantic import (
    BaseModel,
    Field,
)

from lomas_server.models.config import ServerConfig


class ConfigResponse(BaseModel):
    """Model for response to server config queries."""

    config: ServerConfig = Field(default_factory=ServerConfig)
    """The server config."""
