import yaml
from pydantic import BaseModel

from typing_extensions import Dict

from constants import (
    ConfigKeys,
    CONFIG_PATH,
    SECRETS_PATH,
    AdminDBType,
    DatasetStoreType,
    TimeAttackMethod,
)
from utils.error_handler import InternalServerException


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


class DatasetStoreConfig(BaseModel):
    """BaseModel for dataset store configs"""

    ds_store_type: DatasetStoreType


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
                config_data = yaml.safe_load(f)[ConfigKeys.RUNTIME_ARGS][
                    ConfigKeys.SETTINGS
                ]

            # Merge secret data into config data
            with open(secrets_path, "r", encoding="utf-8") as f:
                secret_data = yaml.safe_load(f)
                config_data = self._merge_dicts(config_data, secret_data)

            # Server configuration
            server_config: Server = Server.model_validate(
                config_data[ConfigKeys.SERVER]
            )

            # Admin database
            db_type = AdminDBType(
                config_data[ConfigKeys.DB][ConfigKeys.DB_TYPE]
            )
            admin_database_config = self._validate_admin_db_config(
                db_type, config_data[ConfigKeys.DB]
            )

            # Dataset store
            ds_store_type = DatasetStoreType(
                config_data[ConfigKeys.DATASET_STORE][
                    ConfigKeys.DATASET_STORE_TYPE
                ]
            )
            ds_store_config = self._validate_ds_store_config(
                ds_store_type, config_data[ConfigKeys.DATASET_STORE]
            )

            self._config = Config(
                develop_mode=config_data[ConfigKeys.DEVELOP_MODE],
                server=server_config,
                submit_limit=config_data[ConfigKeys.SUBMIT_LIMIT],
                admin_database=admin_database_config,
                dataset_store=ds_store_config,
            )

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

    def _validate_admin_db_config(
        self, db_type: AdminDBType, config_data: dict
    ) -> DBConfig:
        """Validate admin database based on configuration parameters

        Args:
            db_type (AdminDBType): type of admin database
            config_data (dict): additionnal configuration data
        
        Raises:
        InternalServerException: If the admin database type from the config
            does not exist.

        Returns:
            DBConfig validated admin database configuration
        """
        if db_type == AdminDBType.MONGODB:
            return MongoDBConfig.model_validate(config_data)
        if db_type == AdminDBType.YAML:
            return YamlDBConfig.model_validate(config_data)

        raise InternalServerException(
            f"Admin database type {db_type} not supported."
        )

    def _validate_ds_store_config(
        self, ds_store_type: DatasetStoreType, config_data: dict
    ) -> DatasetStoreConfig:
        """Validate dataset store configuration parameters

        Args:
            ds_store_type (DatasetStoreType): type of admin database
            config_data (dict): additionnal configuration data
        
        Raises:
        InternalServerException: If the dataset store type from the config
            does not exist.

        Returns:
            DatasetStoreConfig validated dataset store configuration
        """
        if ds_store_type == DatasetStoreType.BASIC:
            return DatasetStoreConfig.model_validate(config_data)
        if ds_store_type == DatasetStoreType.LRU:
            return LRUDatasetStoreConfig.model_validate(config_data)

        raise InternalServerException(
            f"Dataset store {ds_store_type} not supported."
        )

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
