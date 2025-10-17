import abc
from typing import Annotated, Literal

from pydantic import (
    AmqpDsn,
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    UrlConstraints,
    computed_field,
)
from pydantic_core import Url
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.models.config import Telemetry, TimeAttack
from lomas_core.models.constants import (
    AuthenticationType,
    OpenDPFeatures,
    PrivateDatabaseType,
)
from lomas_server.auth.auth import FreePassAuthenticator, JWTAuthenticator, UserAuthenticator


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


class AuthenticatorConfig(BaseModel, abc.ABC):
    """BaseModel for Authenticator configs."""

    @abc.abstractmethod
    def user_auth(self) -> UserAuthenticator:
        """Creates an instance of a UserAuthenticator from the provided config.

        Returns:
            UserAuthenticator: The correct authenticator instance.
        """


class FreePassAuthenticatorConfig(AuthenticatorConfig):
    """BaseModel for FreePassAuthenticator config."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]

    def user_auth(self) -> UserAuthenticator:
        return FreePassAuthenticator()


class JWTAuthenticatorConfig(AuthenticatorConfig):
    """BaseModel for JWTAuthenticatorConfig."""

    authentication_type: Literal[AuthenticationType.JWT]
    keycloak_url: HttpUrl
    realm: str

    def user_auth(self) -> UserAuthenticator:
        return JWTAuthenticator(self.keycloak_url, self.realm)


class MongoDBConfig(BaseModel):
    """BaseModel for dataset store configs  in case of a  MongoDB database."""

    url: Annotated[
        AnyUrl,
        UrlConstraints(host_required=True, allowed_schemes=["mongodb", "mongodb+srv"], default_port=27017),
    ]
    username: str
    password: str
    max_pool_size: int = 100
    min_pool_size: int = 2
    max_connecting: int = 2

    @computed_field
    def db_name(self) -> str:
        """Database name."""
        return self.url.path.strip("/")

    @computed_field
    def url_with_options(self) -> str:
        """Construct full DSN including options."""
        dsn = Url.build(
            scheme=self.url.scheme,
            username=self.username,
            password=self.password,
            host=self.url.host,
            port=self.url.port,
            path=self.url.path.strip("/"),
            query=(
                f"authSource={self.db_name}"
                f"&maxPoolSize={self.max_pool_size}&minPoolSize={self.min_pool_size}"
                f"&maxConnecting={self.max_connecting}"
            ),
        )
        return str(dsn)


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

    authenticator: Annotated[
        FreePassAuthenticatorConfig | JWTAuthenticatorConfig, Field(discriminator="authentication_type")
    ]

    admin_database: MongoDBConfig

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]] = {}

    amqp: AmqpConfig

    opendp_features: OpenDPFeatures

    telemetry: Telemetry


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
    server_url: str
    server_service: str
    mg_config: MongoDBConfig
    kc_config: Annotated[KeycloakClientConfig | None, Field(default=None)]
