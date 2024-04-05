import collections.abc
from pydantic import BaseModel

# Temporary workaround this issue:
# https://github.com/pydantic/pydantic/issues/5821
# from typing import Literal
from typing_extensions import Literal
import yaml

from constants import (
    CONFIG_PATH,
    CONF_RUNTIME_ARGS,
    CONF_SETTINGS,
    CONF_DEV_MODE,
    CONF_TIME_ATTACK,
    CONF_DB,
    CONF_DB_TYPE,
    CONF_DB_TYPE_MONGODB,
    CONF_SUBMIT_LIMIT,
    CONF_DATASET_STORE,
    CONF_DATASET_STORE_TYPE,
    CONF_DATASET_STORE_TYPE_LRU,
    CONF_DATASET_STORE_TYPE_BASIC,
    SECRETS_PATH,
)
from utils.error_handler import InternalServerException


class TimeAttack(BaseModel):
    method: Literal["jitter", "stall"]
    magnitude: float = 1


class DBConfig(BaseModel):
    db_type: str = Literal[CONF_DB_TYPE_MONGODB]


class DatasetStoreConfig(BaseModel):
    ds_store_type: Literal[
        CONF_DATASET_STORE_TYPE_BASIC, CONF_DATASET_STORE_TYPE_LRU
    ]


class LRUDatasetStoreConfig(DatasetStoreConfig):
    max_memory_usage: int = None


class MongoDBConfig(DBConfig):
    address: str = None
    port: int = None
    username: str = None
    password: str = None
    db_name: str = None


class Config(BaseModel):
    # Develop mode
    develop_mode: bool = False
    # Server configs
    time_attack: TimeAttack = None

    # A limit on the rate which users can submit answers
    submit_limit: float = 5 * 60  # TODO ticket #145

    admin_database: DBConfig = None

    dataset_store: DatasetStoreConfig = None
    # validator example, for reference
    """ @validator('parties')
    def two_party_min(cls, v):
        assert len(v) >= 2
        return v
    """

    # Yet to determin what this was used for.
    # TODO read this https://docs.pydantic.dev/usage/settings/#secret-support
    # and update how config is loaded (similar to what was done by oblv.)
    """
    class Config:
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                yaml_config,
                env_settings,
                file_secret_settings,
            )
    """


# Utility functions -----------------------------------------------------------


def get_config() -> dict:
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

            def update(d, u):
                for k, v in u.items():
                    if isinstance(v, collections.abc.Mapping):
                        d[k] = update(d.get(k, {}), v)
                    else:
                        d[k] = v
                return d

            update(config_data, secret_data)

        time_attack: TimeAttack = TimeAttack.parse_obj(
            config_data[CONF_TIME_ATTACK]
        )

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
        if ds_store_type == CONF_DATASET_STORE_TYPE_BASIC:
            ds_store_config = DatasetStoreConfig(
                config_data[CONF_DATASET_STORE]
            )
        elif ds_store_type == CONF_DATASET_STORE_TYPE_LRU:
            ds_store_config = LRUDatasetStoreConfig.parse_obj(
                config_data[CONF_DATASET_STORE]
            )

        config: Config = Config(
            develop_mode=config_data[CONF_DEV_MODE],
            time_attack=time_attack,
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
