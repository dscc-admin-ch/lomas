from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import unquote

from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
    HttpUrl,
    UrlConstraints,
    computed_field,
    model_validator,
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


class BackupS3Config(BaseModel):
    """S3 destination for admin database backups."""

    uri: Annotated[
        AnyUrl,
        UrlConstraints(allowed_schemes=["http", "https", "aws", "s3"]),
    ]

    @model_validator(mode="after")
    def check_uri_content(self) -> Self:
        if self.uri.username is None:
            raise ValueError("Backup S3 uri is missing access_key_id.")
        if self.uri.password is None:
            raise ValueError("Backup S3 uri is missing secret_access_key.")

        path = (self.uri.path or "").lstrip("/")
        bucket, _, _ = path.partition("/")
        if not bucket:
            raise ValueError("Backup S3 uri is missing a bucket name.")
        return self

    @computed_field
    def access_key_id(self) -> str:
        return unquote(self.uri.username)

    @computed_field
    def secret_access_key(self) -> str:
        return unquote(self.uri.password)

    @computed_field
    def endpoint_url(self) -> str:
        port = f":{self.uri.port}" if self.uri.port else ""
        return f"{self.uri.scheme}://{self.uri.host}{port}"

    @computed_field
    def bucket(self) -> str:
        path = (self.uri.path or "").lstrip("/")
        bucket, _, _ = path.partition("/")
        return bucket

    @computed_field
    def key_prefix(self) -> str:
        path = (self.uri.path or "").lstrip("/")
        _, _, prefix = path.partition("/")
        return f"{prefix.rstrip('/')}/" if prefix else "lomas-backups/"


class LocalBackupConfig(BaseModel):
    """Local destination for admin database backups."""

    @model_validator(mode="after")
    def is_absolute(self) -> Self:
        if not self.local_directory.is_absolute():
            raise ValueError("Use an absolute path.")
        return self

    local_directory: Path


BackupConfig = LocalBackupConfig | BackupS3Config


class DexAdminConfig(BaseModel):
    url: Url = Field(description="Dex OIDC server addresse")

    @computed_field
    def use_mtls(self) -> bool:
        """Using mTLS ?"""
        return self.url.scheme == "https"


class Config(BaseSettings):
    """Base class for lomas service config."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_server_",
        env_nested_delimiter="__",
        case_sensitive=False,
        cli_kebab_case=True,
        cli_avoid_json=True,
        cli_hide_none_type=True,
        cli_implicit_flags="toggle",
    )

    log_level: str = Field(default="INFO")
    lomas_log_level: str = Field(default="INFO")

    user_host_port: int = Field(default=48080)
    admin_host_port: int = Field(default=48081)

    worker_api_key: str

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]] = {}

    backup: BackupConfig = Field(default=LocalBackupConfig(local_directory="/tmp/lomas-backups"))

    opendp_features: OpenDPFeatures = Field(default=["contrib", "idealized-numerics", "honest-but-curious"])

    telemetry: Telemetry = Field(default_factory=Telemetry, description=CLI_SUPPRESS)

    reload: bool = Field(default=False, description="Reload Process on file change")


class ServerConfig(Config):
    """Lomas server config."""

    bind_ip: str = Field(default="localhost")

    forwarded_allow_ips: list[str] | str = Field(default="*")

    root_path: str = Field(default="/")

    time_attack: TimeAttack = Field(default=TimeAttack(method="jitter", magnitude=1.0))

    # TODO implement rate limiter
    submit_limit: float = Field(default=300.0)
    """A limit on the rate which users can submit queries.

    Not implemented.
    """

    authenticator: AuthenticatorT

    bootstrap: str | None = Field(default=None)

    database_directory: Path = Field(default=Path("/tmp/lomas-db"))

    clean_admin_database: bool = Field(default=False)

    data_directory: Path = Field(default=Path("../data"))

    @computed_field
    def database(self) -> AdminDatabase:  # server
        return LocalAdminDatabase(directory=self.database_directory)


class WorkerConfig(Config):
    tui: bool = Field(default=False, description="Terminal friendly output")

    server_host_addr: str = Field(default="localhost")

    @computed_field
    def admin_api(self) -> HttpUrl:
        return HttpUrl(url=f"http://{self.server_host_addr}:{self.admin_host_port}")


class AdminConfig(BaseSettings):
    """Base model for settings for administrative tasks."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_admin_",
        env_file=".env.lomas_admin",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # We keep both external and service for the following reason
    #   - external is the address to reach the server from the client/user
    #   - service is the address to reach the server from the dashboard/admin job
    # These two can sometimes differ, e.g. if the user is not in the same K8 cluster,
    # or if Lomas is deployed with its own docker network (docker compose case).
    external_url: HttpUrl = Field(description="Lomas server addresse reacheable from the client")
    service_url: HttpUrl = Field(default_factory=lambda data: data["external_url"], description=CLI_SUPPRESS)
    dex_config: DexAdminConfig | None = Field(default=None)
