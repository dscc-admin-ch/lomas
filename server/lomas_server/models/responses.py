from pydantic import (
    BaseModel,
    Field,
)

from lomas_server.models.config import ServerConfig


class ConfigResponse(BaseModel):
    """Model for response to server config queries."""

    config: ServerConfig = Field(default_factory=ServerConfig)
    """The server config."""


class BackupResponse(BaseModel):
    """Model for response to an admin database backup request."""

    location: str
    """Where the backup was written: a local path, or an s3://bucket/key URI."""
    is_s3: bool
    """Whether the backup was uploaded to S3 (True) or written locally (False)."""
    size_bytes: int | None = Field(default=None)
    """Size in bytes of the backup archive."""
