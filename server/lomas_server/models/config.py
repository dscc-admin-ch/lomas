from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AmqpDsn,
    BaseModel,
    Field,
    HttpUrl,
    computed_field,
)
from pydantic_core import Url
from pydantic_settings import CLI_SUPPRESS, BaseSettings, SettingsConfigDict

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

    db_type: Literal[PrivateDatabaseType.S3]
    credentials_name: str
    access_key_id: str
    secret_access_key: str


class AmqpConfig(BaseModel):
    """BaseSettings for Advanced Message Queuing Protocol (AMQP)."""

    url: AmqpDsn
    username: str
    password: str
    heartbeat: str = Field(default="60")

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


class DexAdminConfig(BaseModel):
    url: Url = Field(description="Dex OIDC server addresse")

    @computed_field
    def use_mtls(self) -> bool:
        """Using mTLS ?"""
        return self.url.scheme == "https"


class Server(BaseModel):
    """BaseModel for uvicorn server configs."""

    time_attack: TimeAttack = Field(default=TimeAttack(method="jitter", magnitude=1.0))
    submit_limit: float = Field(default=300.0)
    """A limit on the rate which users can submit queries."""
    host_ip: str = Field(default="localhost")
    host_port: int = Field(default=48080)
    log_level: str = Field(default="INFO")
    lomas_log_level: str = Field(default="INFO")
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
    server: Server = Field(default_factory=Server)

    authenticator: AuthenticatorT

    dex_config: Annotated[DexAdminConfig | None, Field(default=None)]

    bootstrap: str | None = Field(default=None)

    admin_database_url: Path = Field(default=Path("/tmp/admin.db"))

    clean_admin_database: bool = Field(default=False)

    data_directory: Path = Field(default=Path("../data"))

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]] = {}

    amqp: AmqpConfig

    opendp_features: OpenDPFeatures = Field(default=["contrib", "idealized-numerics", "honest-but-curious"])

    telemetry: Telemetry = Field(default_factory=Telemetry)

    @computed_field
    def database(self) -> AdminDatabase:
        return LocalAdminDatabase(path=self.admin_database_url)


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
    server_url: HttpUrl = Field(description="Lomas server addresse reacheable from the client")
    server_service: HttpUrl = Field(default_factory=lambda data: data["server_url"], description=CLI_SUPPRESS)
    dex_config: DexAdminConfig | None = Field(default=None)
