import collections.abc

import yaml
from constants import (
    CONF_DATASET_STORE,
    CONF_DATASET_STORE_TYPE,
    CONF_DB,
    CONF_DB_TYPE,
    CONF_DB_TYPE_MONGODB,
    CONF_DEV_MODE,
    CONF_RUNTIME_ARGS,
    CONF_SERVER,
    CONF_SETTINGS,
    CONF_SUBMIT_LIMIT,
    CONFIG_PATH,
    SECRETS_PATH,
    ConfDatasetStore,
)
from pydantic import BaseModel

# Temporary workaround this issue:
# https://github.com/pydantic/pydantic/issues/5821
# from typing import Literal
from typing_extensions import Dict, Literal
from utils.error_handler import InternalServerException


class TimeAttack(BaseModel):
    method: Literal["jitter", "stall"]
    magnitude: float


class Server(BaseModel):
    time_attack: TimeAttack
    host_ip: str
    host_port: int
    log_level: str
    reload: bool
    workers: int


class DBConfig(BaseModel):
    db_type: str = CONF_DB_TYPE_MONGODB


class DatasetStoreConfig(BaseModel):
    ds_store_type: ConfDatasetStore


class LRUDatasetStoreConfig(DatasetStoreConfig):
    max_memory_usage: int


class MongoDBConfig(DBConfig):
    address: str
    port: int
    username: str
    password: str
    db_name: str


class Config(BaseModel):
    # Develop mode
    develop_mode: bool

    # Server configs
    server: Server

    # A limit on the rate which users can submit answers
    submit_limit: float

    admin_database: DBConfig

    dataset_store: DatasetStoreConfig

    # validator example, for reference
    """ @validator('parties')
    def two_party_min(cls, v):
        assert len(v) >= 2
        return v
    """


# Utility functions -----------------------------------------------------------


def get_config() -> Config:
    """
    Loads the config and the secret data from disk,
    merges them and returns the config object.
    """
    try:
        with open(CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)[CONF_RUNTIME_ARGS][CONF_SETTINGS]

        # Merge secret data into config data
        with open(SECRETS_PATH, "r") as f:
            secret_data = yaml.safe_load(f)

            def update(d: dict, u: Dict[str, Dict[str, str]]) -> dict:
                for k, v in u.items():
                    if isinstance(v, collections.abc.Mapping):
                        d[k] = update(d.get(k, {}), v)
                    else:
                        d[k] = v
                return d

            update(config_data, secret_data)

        server_config: Server = Server.parse_obj(config_data[CONF_SERVER])

        db_type = config_data[CONF_DB][CONF_DB_TYPE]
        if db_type == CONF_DB_TYPE_MONGODB:
            admin_database_config = MongoDBConfig.parse_obj(
                config_data[CONF_DB]
            )
        else:
            raise InternalServerException(
                f"User database type {db_type} not supported."
            )

        ds_store_type = config_data[CONF_DATASET_STORE][
            CONF_DATASET_STORE_TYPE
        ]
        match ds_store_type:
            case ConfDatasetStore.BASIC:
                ds_store_config = DatasetStoreConfig(
                    config_data[CONF_DATASET_STORE]
                )
            case ConfDatasetStore.LRU:
                ds_store_config = LRUDatasetStoreConfig.parse_obj(
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
            + f"or missing fields: {e}"
        )

    return config


"""
def reload_config() -> Config:
    # Potentially?
    return None
"""
