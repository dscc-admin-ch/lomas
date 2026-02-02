from functools import cached_property

import requests
from pydantic import HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.models.config import OIDCConfig, Telemetry


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
    user_name: str
    """User name."""
    # TODO add option for devide auth flow.
    user_password: str | None
    """If provided, will."""
    oidc_discovery_url: HttpUrl
    """The oidc provier discovery Url."""
    telemetry: Telemetry
    """Telemetry Settings."""

    @computed_field
    def keycloak_use_tls(self) -> bool:
        """Using TLS for keycloak?"""
        return self.oidc_discovery_url.scheme == "https"

    @computed_field
    def lomas_service_use_tls(self) -> bool:
        """Using TLS for lomas service?"""
        return self.app_url.scheme == "https"

    @cached_property
    def oidc_config(self) -> OIDCConfig:
        """Returns the oidc provider config."""
        response = requests.get("{self.oidc_discovery_url}")
        response.raise_for_status()

        return OIDCConfig.model_validate_json(response.json())
