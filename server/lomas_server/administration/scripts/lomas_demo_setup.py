import logging

from pydantic_settings import SettingsConfigDict

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

    path_prefix: str = ""
    user_yaml: str = "/data/collections/user_collection.yaml"
    dataset_yaml: str = "/data/collections/dataset_collection.yaml"


def add_lomas_demo_data(config: DemoAdminConfig) -> None:
    """
    Adds the demo data to the admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    logging.info("Creating user collection")
    config.database.add_users_via_yaml(
        clean=True,
        yaml_file=config.user_yaml,
        path_prefix=config.path_prefix,
    )
    if config.kc_config is not None:
        add_kc_users_via_yaml(
            config.kc_config,
            yaml_file=config.user_yaml,
            clean=False,
            overwrite=True,
            path_prefix=config.path_prefix,
        )

    logging.info("Creating datasets and metadata collection")
    config.database.add_datasets_via_yaml(
        clean=True,
        yaml_file=config.dataset_yaml,
        path_prefix=config.path_prefix,
    )

    logging.info("Empty archives")
    config.database.drop_archive()


def lomas_demo_setup() -> None:
    """Script for setting up demo users and dataset."""
    demo_config = DemoAdminConfig()
    add_lomas_demo_data(demo_config)


if __name__ == "__main__":
    lomas_demo_setup()
