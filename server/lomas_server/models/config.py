from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
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
    user_host_port: int = Field(default=48080)
    admin_host_port: int = Field(default=48081)
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
        cli_kebab_case=True,
        cli_avoid_json=True,
        cli_hide_none_type=True,
        cli_implicit_flags="toggle",
    )

    # Server configs
    server: Server = Field(default=Server())

    authenticator: AuthenticatorT

    dex_config: Annotated[DexAdminConfig | None, Field(default=None)]

    bootstrap: str | None = Field(default=None)

    database_directory: Path = Field(default=Path("/tmp/lomas-db"))

    clean_admin_database: bool = Field(default=False)

    data_directory: Path = Field(default=Path("../data"))

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]] = {}

    opendp_features: OpenDPFeatures = Field(default=["contrib", "idealized-numerics", "honest-but-curious"])

    telemetry: Telemetry = Field(default_factory=Telemetry, description=CLI_SUPPRESS)

    tui: bool = Field(default=False, description="Terminal friendly output")

    reload: bool = Field(default=False, description="Reload Process on file change")

    @computed_field
    def database(self) -> AdminDatabase:
        return LocalAdminDatabase(directory=self.database_directory)


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
