from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    UrlConstraints,
    model_validator,
)

from lomas_core.models.constants import (
    TimeAttackMethod,
)


class TimeAttack(BaseModel):
    """BaseModel for configs to prevent timing attacks."""

    method: TimeAttackMethod
    magnitude: float


class Telemetry(BaseModel):
    """Telemetry config."""

    enabled: bool
    service_name: Annotated[str, Field(default="lomas-server-app")]
    service_id: Annotated[str, Field(default="default-host")]
    collector_endpoint: Annotated[HttpUrl, UrlConstraints(default_port=4317)] | None = None
    collector_insecure: Annotated[bool, Field(default=False)]
    collector_log_correlation: Annotated[bool, Field(default=False)]

    @model_validator(mode="after")
    def options_set_if_enabled(self) -> Self:
        """Ensures that if enabled is set to True, all other fields are specified.

        Raises:
            ValueError: If any of the fields is not specified while enabled is True.
        """
        if self.enabled:
            missing = [k for k, v in dict(self).items() if v is None]
            if len(missing) > 0:
                raise ValueError(
                    f"If enabled set to True, all other fields must be specified. Missing fields: {missing}"
                )

        return self


class OIDCConfig(BaseModel):
    """Base model for oidc config returned from discovery endpoint."""

    # Only useful (to us) fields are present in the model.
    model_config = ConfigDict(extra="ignore")

    issuer: HttpUrl
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    jwks_uri: HttpUrl
    userinfo_endpoint: HttpUrl
    device_authorization_endpoint: HttpUrl
    introspection_endpoint: HttpUrl
