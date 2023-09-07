from pydantic import BaseModel

# Temporary workaround this issue:
# https://github.com/pydantic/pydantic/issues/5821
# from typing import Literal
from typing_extensions import Literal
import yaml

from utils.constants import (
    CONFIG_PATH,
    CONF_RUNTIME_ARGS,
    CONF_SETTINGS,
    CONF_DEV_MODE,
    CONF_TIME_ATTACK,
    CONF_DB,
    CONF_DB_TYPE,
    CONF_DB_TYPE_MONGODB,
    CONF_DB_TYPE_YAML,
    CONF_SUBMIT_LIMIT,
)
from utils.loggr import LOG


class TimeAttack(BaseModel):
    method: Literal["jitter", "stall"]
    magnitude: float = 1


class DBConfig(BaseModel):
    db_type: str = Literal["mongodb", "yaml"]


class MongoDBConfig(DBConfig):
    address: str = None
    port: int = None
    username: str = None
    password: str = None
    db_name: str = None


class YAMLDBConfig(DBConfig):
    db_file: str = None


class Config(BaseModel):
    # Develop mode
    develop_mode: bool = False
    # Server configs
    time_attack: TimeAttack = None

    # A limit on the rate which users can submit answers
    submit_limit: float = (
        5 * 60
    )  # TODO not used for the moment, kept as a simple example field for now.

    admin_database: DBConfig = None
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
    Loads the config from disk, and returns the config object.
    """
    try:
        with open(CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)[CONF_RUNTIME_ARGS][CONF_SETTINGS]

        time_attack: TimeAttack = TimeAttack.parse_obj(
            config_data[CONF_TIME_ATTACK]
        )

        db_type = config_data[CONF_DB][CONF_DB_TYPE]
        if db_type == CONF_DB_TYPE_MONGODB:
            admin_database_config = MongoDBConfig.parse_obj(
                config_data[CONF_DB]
            )
        elif db_type == CONF_DB_TYPE_YAML:
            admin_database_config = YAMLDBConfig.parse_obj(
                config_data[CONF_DB]
            )
        else:
            raise Exception(f"User database type {db_type} not supported.")

        config: Config = Config(
            develop_mode=config_data[CONF_DEV_MODE],
            time_attack=time_attack,
            submit_limit=config_data[CONF_SUBMIT_LIMIT],
            admin_database=admin_database_config,
        )

    except Exception as e:
        LOG.error(
            f"Could not read config from disk at {CONFIG_PATH} \
                or missing fields"
        )
        raise e

    return config


"""
def reload_config() -> Config:
    # Potentially?
    return None
"""
