import os

import yaml
from pydantic import BaseModel

from lomas_core.error_handler import InternalServerException

# Get config and secrets from correct location
if "LOMAS_DASHBOARD_CONFIG_PATH" in os.environ:
    CONFIG_PATH = f"""{os.environ.get("LOMAS_DASHBOARD_CONFIG_PATH")}"""
    print(CONFIG_PATH)
else:
    CONFIG_PATH = "/usr/lomas_dashboard/dashboard.yaml"


class Config(BaseModel):
    """Dashboard runtime config."""

    server_url: str
    server_service: str


class ConfigLoader:
    """Singleton object that holds the config for the dashboard.

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

    def load_config(self, config_path: str = CONFIG_PATH) -> None:
        """
        Loads the config and the secret data from disk,.

        Merges them and returns the config object.

        Args:
            config_path (str, optional):
                The config filepath. Defaults to CONFIG_PATH.

        Raises:
            InternalServerException: If the config cannot be
                correctly interpreted.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            self._config = Config.model_validate(config_data)

        except Exception as e:
            raise InternalServerException(
                f"Could not read config from disk at {config_path} or missing fields: {e}"
            ) from e

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
