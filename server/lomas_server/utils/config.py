import yaml
from pydantic import BaseModel

# Temporary workaround this issue:
# https://github.com/pydantic/pydantic/issues/5821
# from typing import Literal
from typing_extensions import Any, Dict, Literal

from constants import (
    CONF_DATASET_STORE,
    CONF_DATASET_STORE_TYPE,
    CONF_DB,
    CONF_DB_TYPE,
    CONF_DEV_MODE,
    CONF_RUNTIME_ARGS,
    CONF_SERVER,
    CONF_SETTINGS,
    CONF_SUBMIT_LIMIT,
    CONFIG_PATH,
    SECRETS_PATH,
    AdminDBType,
    ConfDatasetStore,
)
from utils.error_handler import InternalServerException


class TimeAttack(BaseModel):
    """BaseModel for configs to prevent timing attacks"""

    method: Literal["jitter", "stall"]
    magnitude: float


class Server(BaseModel):
    """BaseModel for uvicorn server configs"""

    time_attack: TimeAttack
    host_ip: str
    host_port: int
    log_level: str
    reload: bool
    workers: int


class DatasetStoreConfig(BaseModel):
    """BaseModel for dataset store configs"""

    ds_store_type: ConfDatasetStore


class LRUDatasetStoreConfig(DatasetStoreConfig):
    """BaseModel for dataset store configs in case of a LRU dataset store"""

    max_memory_usage: int


class DBConfig(BaseModel):
    """BaseModel for database type config"""

    db_type: str = AdminDBType


class YamlDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a Yaml database"""

    db_file: str


class MongoDBConfig(DBConfig):
    """BaseModel for dataset store configs  in case of a  MongoDB database"""

    address: str
    port: int
    username: str
    password: str
    db_name: str


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

    admin_database: DBConfig

    dataset_store: DatasetStoreConfig


# Utility functions -----------------------------------------------------------


class ConfigLoader:
    """Singleton object that holds the config for the server.

    Initialises the config by calling load_config() with its
    default arguments.

    The config can be reloaded by calling load_config with
    other arguments.
    """

    _instance = None
    _config = None

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
                config_data = yaml.safe_load(f)[CONF_RUNTIME_ARGS][
                    CONF_SETTINGS
                ]

            # Merge secret data into config data
            with open(secrets_path, "r", encoding="utf-8") as f:
                secret_data = yaml.safe_load(f)

                def update(
                    d: Dict[str, Any], u: Dict[str, Any]
                ) -> Dict[str, Any]:
                    for k, v in u.items():
                        if isinstance(v, dict):
                            d[k] = update(d.get(k, {}), v)
                        else:
                            d[k] = v
                    return d

                update(config_data, secret_data)

            server_config: Server = Server.model_validate(
                config_data[CONF_SERVER]
            )

            db_type = config_data[CONF_DB][CONF_DB_TYPE]
            match db_type:
                case AdminDBType.MONGODB_TYPE:
                    admin_database_config = MongoDBConfig.model_validate(
                        config_data[CONF_DB]
                    )
                case AdminDBType.YAML_TYPE:
                    admin_database_config = YamlDBConfig.model_validate(
                        config_data[CONF_DB]
                    )  # type: ignore
                case _:
                    raise InternalServerException(
                        f"Admin database type {db_type} not supported."
                    )

            ds_store_type = config_data[CONF_DATASET_STORE][
                CONF_DATASET_STORE_TYPE
            ]
            match ds_store_type:
                case ConfDatasetStore.BASIC:
                    ds_store_config = DatasetStoreConfig.model_validate(
                        config_data[CONF_DATASET_STORE]
                    )
                case ConfDatasetStore.LRU:
                    ds_store_config = LRUDatasetStoreConfig.model_validate(
                        config_data[CONF_DATASET_STORE]
                    )
                case _:
                    raise InternalServerException(
                        f"Dataset store {ds_store_type} not supported."
                    )

            config: Config = Config(
                develop_mode=config_data[CONF_DEV_MODE],
                server=server_config,
                submit_limit=config_data[CONF_SUBMIT_LIMIT],
                admin_database=admin_database_config,
                dataset_store=ds_store_config,
            )
        except Exception as e:
            raise InternalServerException(
                f"Could not read config from disk at {CONFIG_PATH}"
                + f" or missing fields: {e}"
            ) from e

        self._config = config

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
        return self._config  # type: ignore


CONFIG_LOADER = ConfigLoader()


def get_config() -> Config:
    """
    Get the config from the ConfigLoader Singleton instance.

    Returns:
        Config: The config.
    """
    return CONFIG_LOADER.get_config()
