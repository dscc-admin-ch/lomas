from pydantic import BaseModel
from typing import Literal, List
import yaml

from utils.constants import CONFIG_PATH
from utils.loggr import LOG


class TimeAttack(BaseModel):
    method: Literal["jitter", "stall"]
    magnitude: float = 1


class Config(BaseModel):
    # Service configs
    users: List[dict]

    datasets: List[str] = []

    # Server configs
    time_attack: TimeAttack = None

    # A limit on the rate which users can submit answers
    submit_limit: float = (
        5 * 60
    )  # TODO not used for the moment, kept as a simple example field for now.

    # validator example, for reference
    """ @validator('parties')
    def two_party_min(cls, v):
        assert len(v) >= 2
        return v
    """

    # Yet to determin what this was used for.
    # TODO read this https://docs.pydantic.dev/usage/settings/#secret-support
    # and update how config is loaded (similar to what is done by oblv.)
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
    Returns the global config object if not None.
    If not already loaded, loads it from disk, sets it as the global config
    and returns it.
    """
    import globals

    if globals.CONFIG is not None:
        return globals.CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)["runtime_args"]["settings"]

        time_attack: TimeAttack = TimeAttack.parse_obj(
            config_data["time_attack"]
        )
        config: Config = Config(
            users=config_data["users"],
            time_attack=time_attack,
            submit_limit=config_data["submit_limit"],
        )
    except Exception as e:
        LOG.error(
            f"Could not read config from disk at {CONFIG_PATH} \
                or missing fields"
        )
        raise e

    globals.CONFIG = config

    return config_data


"""
def reload_config() -> Config:
    # Potentially?
    return None
"""
