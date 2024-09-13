from typing import Dict, List, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field

from lomas_server.constants import (
    CONFIG_PATH,
    SECRETS_PATH,
    AdminDBType,
    ConfigKeys,
    PrivateDatabaseType,
    TimeAttackMethod,
)
from lomas_server.utils.error_handler import InternalServerException


class TimeAttack(BaseModel):
    """BaseModel for configs to prevent timing attacks"""

    method: TimeAttackMethod
    magnitude: float


class Server(BaseModel):
    """BaseModel for uvicorn server configs"""

    time_attack: TimeAttack
    host_ip: str
    host_port: int
    log_level: str
    reload: bool
    workers: int


class DBConfig(BaseModel):
    """BaseModel for database type config"""


class YamlDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a Yaml database"""

    db_type: Literal[AdminDBType.YAML]  # type: ignore
    db_file: str


class MongoDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a  MongoDB database"""

    db_type: Literal[AdminDBType.MONGODB]  # type: ignore
    address: str
    port: int
    username: str
    password: str
    db_name: str


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
    """BaseModel for openDP librairy config"""

    contrib: bool
    floating_point: bool
    honest_but_curious: bool


class DPLibraryConfig(BaseModel):
    """BaseModel for DP librairies config"""

    opendp: OpenDPConfig


class Config(BaseModel):
    """
    Server runtime config.
    """

    # Develop mode
    develop_mode: bool

    # Server configs
    server: Server

    # A limit on the rate which users can submit answers
    submit_limit: float

    admin_database: Union[MongoDBConfig, YamlDBConfig] = Field(
        ..., discriminator="db_type"
    )

    private_db_credentials: List[Union[S3CredentialsConfig]] = Field(
        ..., discriminator="db_type"
    )

    dp_libraries: DPLibraryConfig


class ConfigLoader:
    """Singleton object that holds the config for the server.

    Initialises the config by calling load_config() with its
    default arguments.

    The config can be reloaded by calling load_config with
    other arguments.
    """

    _instance = None
    _config: Config | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_config(
        self, config_path: str = CONFIG_PATH, secrets_path: str = SECRETS_PATH
    ) -> None:
        """
        Loads the config and the secret data from disk,
        merges them and returns the config object.

        Args:
            config_path (str, optional):
                The config filepath. Defaults to CONFIG_PATH.
            secrets_path (str, optional):
                The secrets filepath. Defaults to SECRETS_PATH.

        Raises:
            InternalServerException: If the config cannot be
                correctly interpreted.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)[ConfigKeys.RUNTIME_ARGS][
                    ConfigKeys.SETTINGS
                ]

            # Merge secret data into config data
            with open(secrets_path, "r", encoding="utf-8") as f:
                secret_data = yaml.safe_load(f)
                config_data = self._merge_dicts(config_data, secret_data)

            self._config = Config.model_validate(config_data)

        except Exception as e:
            raise InternalServerException(
                f"Could not read config from disk at {config_path}"
                + f" or missing fields: {e}"
            ) from e

    def _merge_dicts(self, d: Dict, u: Dict) -> Dict:
        """Recursively add dictionnary u to dictionnary v

        Args:
            d (Dict): dictionnary to add data to
            u (Dict): dictionnary to be added to d

        Returns:
            d (Dict): dictionnary d and u merged recursively
        """
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._merge_dicts(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    def set_config(self, config: Config) -> None:
        """
        Set the singleton's config to config.

        Args:
            config (Config): The new config.
        """
        self._config = config

    def get_config(self) -> Config:
        """
        Get the config.

        Returns:
            Config: The config.
        """
        if self._config is None:
            self.load_config()
        assert isinstance(self._config, Config)  # Helps mypy
        return self._config


CONFIG_LOADER = ConfigLoader()


def get_config() -> Config:
    """
    Get the config from the ConfigLoader Singleton instance.

    Returns:
        Config: The config.
    """
    return CONFIG_LOADER.get_config()
