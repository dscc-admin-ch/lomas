from pydantic import (
    BaseModel,
    Field,
)

from lomas_server.models.config import Config


class ConfigResponse(BaseModel):
    """Model for response to server config queries."""

    config: Config = Field(default_factory=Config)
    """The server config."""
