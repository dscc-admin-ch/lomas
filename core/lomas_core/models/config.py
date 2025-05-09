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

from lomas_core.models.constants import (
    AuthenticationType,
    DefaultLoggingConf,
    OpenDPFeatures,
    PrivateDatabaseType,
    TimeAttackMethod,
)
from lomas_server.auth.auth import FreePassAuthenticator, JWTAuthenticator, UserAuthenticator


class TimeAttack(BaseModel):
    """BaseModel for configs to prevent timing attacks."""

    method: TimeAttackMethod
    magnitude: float


class Server(BaseModel):
    """BaseModel for uvicorn server configs."""

    time_attack: TimeAttack
    submit_limit: float
    """A limit on the rate which users can submit answers."""
    host_ip: str
    host_port: int
    log_level: str
    reload: bool = Field(default=False)


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


class PrivateDBCredentials(BaseModel):
    """BaseModel for private database credentials."""


class S3CredentialsConfig(PrivateDBCredentials):
    """BaseModel for S3 database credentials."""

    model_config = ConfigDict(extra="allow")

    db_type: Literal[PrivateDatabaseType.S3]
    credentials_name: str
    access_key_id: str
    secret_access_key: str


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


class AmqpConfig(BaseModel):
    """BaseSettings for Advanced Message Queuing Protocol (AMQP)."""

    url: AmqpDsn
    username: str
    password: str

    @computed_field
    def dsn(self) -> str:
        """Construct full DSN including credentials."""
        dsn = Url.build(
            scheme=self.url.scheme,
            username=self.username,
            password=self.password,
            host=self.url.host,
            port=self.url.port,
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


class Telemetry(BaseModel):
    """Telemetry config."""

    enabled: bool
    service_name: str = Field(default="lomas-server-app")
    service_id: str = Field(default="default-host")
    collector_endpoint: Annotated[HttpUrl, UrlConstraints(default_port=4317)]
    collector_insecure: bool = Field(default=False)
    collector_log_correlation: bool = Field(default=False)


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

    private_db_credentials: dict[int, Annotated[S3CredentialsConfig, Field(discriminator="db_type")]]

    logging_config: dict = Field(default=DefaultLoggingConf)

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

    server_url: str
    server_service: str
    mg_config: MongoDBConfig
    kc_config: Annotated[KeycloakClientConfig | None, Field(default=None)]
