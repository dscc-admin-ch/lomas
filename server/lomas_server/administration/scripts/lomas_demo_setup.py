from pathlib import Path

from pydantic import Field
from pydantic_settings import SettingsConfigDict
from rich.pretty import pprint

from lomas_server.administration.keycloak_admin import add_kc_users_via_yaml
from lomas_server.models.config import AdminConfig


class DemoAdminConfig(AdminConfig):
    """Extension of Admin config for demo setup."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_admin_",
        env_file=".env.lomas_admin",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    path_prefix: Path = Field(default=".")
    user_yaml: Path = Field(default="/data/collections/user_collection.yaml")
    dataset_yaml: Path = Field(default="/data/collections/dataset_collection.yaml")


def add_lomas_demo_data(config: DemoAdminConfig) -> None:
    """
    Adds the demo data to the admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    pprint("Creating user collection from Config")
    pprint(config)

    user_yaml_file = config.path_prefix / config.user_yaml.relative_to("/")
    dataset_yaml_file = config.path_prefix / config.dataset_yaml.relative_to("/")

    config.database.add_users_via_yaml(
        clean=True,
        yaml_file=user_yaml_file,
    )
    if config.kc_config is not None:
        add_kc_users_via_yaml(
            config.kc_config,
            yaml_file=user_yaml_file,
            clean=False,
            overwrite=True,
        )

    pprint("Creating datasets and metadata collection")
    config.database.add_datasets_via_yaml(
        clean=True,
        yaml_file=dataset_yaml_file,
        path_prefix=str(config.path_prefix),
    )

    pprint("Empty archives")
    config.database.drop_archive()


def lomas_demo_setup() -> None:
    """Script for setting up demo users and dataset."""
    demo_config = DemoAdminConfig()
    add_lomas_demo_data(demo_config)


if __name__ == "__main__":
    lomas_demo_setup()
