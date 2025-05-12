from pydantic import HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.models.config import Telemetry


class ClientConfig(BaseSettings):
    """Config model for the HTTP client."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_client_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    app_url: HttpUrl
    """The base URL for the API server."""
    dataset_name: str
    """The name of the dataset to be accessed or manipulated."""
    client_id: str
    """Client id of the users's associated service account."""
    client_secret: str
    """Client secret of the users's associated service account."""
    keycloak_url: HttpUrl
    """The keycloak Url."""
    realm: str
    """The realm, if using jwt authentication."""
    telemetry: Telemetry
    """Telemetry Settings."""

    @computed_field
    def keycloak_use_tls(self) -> bool:
        """Using TLS ?"""
        return self.keycloak_url.scheme == "https"

    @computed_field
    def token_endpoint(self) -> str:
        """Build OAuth2 token endpoint."""
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
