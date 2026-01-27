from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AmqpDsn,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
)
from pydantic_core import Url
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.models.config import Telemetry, TimeAttack
from lomas_core.models.constants import (
    OpenDPFeatures,
    PrivateDatabaseType,
)
from lomas_server.admin_database import AdminDatabase, LocalAdminDatabase
from lomas_server.auth.auth import AuthenticatorT


class PrivateDBCredentials(BaseModel):
    """BaseModel for private database credentials."""


class S3CredentialsConfig(PrivateDBCredentials):
    """BaseModel for S3 database credentials."""

    model_config = ConfigDict(extra="allow")

    db_type: Literal[PrivateDatabaseType.S3]
    credentials_name: str
    access_key_id: str
    secret_access_key: str


class AmqpConfig(BaseModel):
    """BaseSettings for Advanced Message Queuing Protocol (AMQP)."""

    url: AmqpDsn
    username: str
    password: str
    heartbeat: str

    @computed_field
    def dsn(self) -> str:
        """Construct full DSN including credentials."""
        dsn = Url.build(
            scheme=self.url.scheme,
            username=self.username,
            password=self.password,
            host=self.url.host,
            port=self.url.port,
            query=f"heartbeat={self.heartbeat}",
        )
        return str(dsn)

    @computed_field
    def base_url(self) -> str:
        """Queue base URL."""
        base_url = Url.build(
            scheme=self.url.scheme,
            host=self.url.host,
            port=self.url.port,
        )
        return str(base_url)


class Server(BaseModel):
    """BaseModel for uvicorn server configs."""

    time_attack: TimeAttack
    submit_limit: float
    """A limit on the rate which users can submit answers."""
    host_ip: str
    host_port: int
    log_level: str
    reload: bool = Field(default=False)
    forwarded_allow_ips: list[str] | str = Field(default="*")
    root_path: str = Field(default="/api")


class Config(BaseSettings):
    """Server runtime config."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_service_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Server configs
    server: Server

    authenticator: AuthenticatorT

    admin_database_url: Path

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]] = {}

    amqp: AmqpConfig

    opendp_features: OpenDPFeatures

    telemetry: Telemetry

    @computed_field
    def database(self) -> AdminDatabase:
        return LocalAdminDatabase(path=self.admin_database_url)


class KeycloakClientConfig(BaseModel):
    """Base model for Keycloak client config."""

    url: HttpUrl
    realm: str
    client_id: str
    client_secret: str

    @computed_field
    def use_tls(self) -> bool:
        """Using TLS ?"""
        return self.url.scheme == "https"

    @computed_field
    def token_endpoint(self) -> str:
        """Build OAuth2 token endpoint."""
        return f"{self.url}/realms/{self.realm}/protocol/openid-connect/token"


class DexAdminConfig(BaseModel):
    url: Url

    @computed_field
    def use_mtls(self) -> bool:
        """Using mTLS ?"""
        return self.url.scheme == "https"


class AdminConfig(BaseSettings):
    """Base model for settings for administrative tasks."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_admin_",
        env_file=".env.lomas_admin",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # We keep both url and service for the following reason
    #   - url is the address to reach the server from the client/user
    #   - service is the address to reach the server from the dashboard/admin job
    # These two can sometimes differ, e.g. if the user is not in the same K8 cluster,
    # or if Lomas is deployed with its own docker network (docker compose case).
    server_url: HttpUrl
    server_service: HttpUrl
    database_url: Path
    dex_config: Annotated[DexAdminConfig | None, Field(default=None)]

    @computed_field
    def database(self) -> AdminDatabase:
        return LocalAdminDatabase(path=self.database_url)
