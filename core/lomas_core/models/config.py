from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from lomas_core.models.constants import (
    AdminDBType,
    AuthenticationType,
    PrivateDatabaseType,
    TimeAttackMethod,
)


class TimeAttack(BaseModel):
    """BaseModel for configs to prevent timing attacks."""

    method: TimeAttackMethod
    magnitude: float


class Server(BaseModel):
    """BaseModel for uvicorn server configs."""

    time_attack: TimeAttack
    host_ip: str
    host_port: int
    log_level: str
    reload: bool
    workers: int


class DBConfig(BaseModel):
    """BaseModel for database type config."""


class YamlDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a Yaml database."""

    db_type: Literal[AdminDBType.YAML]  # type: ignore
    db_file: str


class MongoDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a  MongoDB database."""

    db_type: Literal[AdminDBType.MONGODB] = AdminDBType.MONGODB  # type: ignore
    address: str
    port: int
    username: str
    password: str
    db_name: str
    max_pool_size: int
    min_pool_size: int
    max_connecting: int


class PrivateDBCredentials(BaseModel):
    """BaseModel for private database credentials."""


class S3CredentialsConfig(PrivateDBCredentials):
    """BaseModel for S3 database credentials."""

    model_config = ConfigDict(extra="allow")

    db_type: Literal[PrivateDatabaseType.S3]  # type: ignore
    credentials_name: str
    access_key_id: str
    secret_access_key: str


class OpenDPConfig(BaseModel):
    """BaseModel for openDP library config."""

    contrib: bool
    floating_point: bool
    honest_but_curious: bool


class DPLibraryConfig(BaseModel):
    """BaseModel for DP librairies config."""

    opendp: OpenDPConfig


class AuthenticatorConfig(BaseModel):
    """BaseModel for Authenticator configs."""


class FreePassAuthenticatorConfig(AuthenticatorConfig):
    """BaseModel for FreePassAuthenticator config."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]  # type: ignore


class JWTAuthenticatorConfig(AuthenticatorConfig):
    """BaseModel for JWTAuthenticatorConfig."""

    authentication_type: Literal[AuthenticationType.JWT]  # type: ignore

    keycloak_address: str
    keycloak_port: int
    keycloak_use_tls: bool
    realm: str


class Config(BaseModel):
    """Server runtime config."""

    # Develop mode
    develop_mode: bool

    # Server configs
    server: Server

    # A limit on the rate which users can submit answers
    submit_limit: float

    authenticator: Annotated[
        Union[FreePassAuthenticatorConfig, JWTAuthenticatorConfig], Field(discriminator="authentication_type")
    ]

    admin_database: Annotated[Union[MongoDBConfig, YamlDBConfig], Field(discriminator="db_type")]

    private_db_credentials: List[Annotated[Union[S3CredentialsConfig], Field(discriminator="db_type")]]

    dp_libraries: DPLibraryConfig


class KeycloakClientConfig(BaseModel):
    """Base model for Keycloak client config."""

    address: str
    port: int
    use_tls: bool
    realm: str
    client_id: str
    client_secret: str


class AdminConfig(BaseSettings):

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_adm_",
        env_file="lomas_admin.env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    mg_config: MongoDBConfig
    kc_config: Annotated[Optional[KeycloakClientConfig], Field(default=None)]
