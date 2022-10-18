from pydantic import BaseSettings, BaseModel, validator
from typing import Literal, List, Dict, Any
import functools 

import yaml
from yaml.loader import SafeLoader

OBLV_CONFIG_PATH = '/usr/runtime.yaml'

def yaml_config(settings: BaseSettings) -> Dict[str, Any]:
    try:
        with open(OBLV_CONFIG_PATH, 'r') as f:
            config_data = yaml.safe_load(f)
    except:
        config_data = {}
    return config_data


class TimeAttack(BaseModel):
    method: Literal["jitter", "stall"] 
    magnitude: float

class Settings(BaseSettings):
    parties: List[str] 
    rank_coef: float 
    time_attack: TimeAttack = None

    # a limit on the rate which users can submit answers
    submit_limit: float = 5*60

    no_leaders_on_leaderboard: float = None

    @validator('parties')
    def two_party_min(cls, v):
        assert len(v) >= 2
        return v

    @validator('rank_coef')
    def positive_rank_coef(cls, v):
        assert v > 0
        return v

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

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()

