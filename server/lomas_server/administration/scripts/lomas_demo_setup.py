import logging

from pydantic_settings import SettingsConfigDict

from lomas_core.models.config import AdminConfig
from lomas_server.administration.lomas_admin import add_lomas_users_via_yaml
from lomas_server.administration.mongodb_admin import (
    add_datasets_via_yaml,
    drop_collection,
)


class DemoAdminConfig(AdminConfig):
    """"Extension of Admin config for demo setup."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_admin_",
        env_file="lomas_admin.env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    user_yaml: str = "/data/collections/user_collection.yaml"
    dataset_yaml: str = "/data/collections/dataset_collection.yaml"


def add_lomas_demo_data(
    config: DemoAdminConfig,
) -> None:
    """
    Adds the demo data to the mongodb admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    logging.info("Creating user collection")
    add_lomas_users_via_yaml(
        config,
        clean=True,
        overwrite=True,
        yaml_file=config.user_yaml,
    )

    logging.info("Creating datasets and metadata collection")
    add_datasets_via_yaml(
        config.mg_config,
        clean=True,
        overwrite_datasets=True,
        overwrite_metadata=True,
        yaml_file=config.dataset_yaml,
    )

    logging.info("Empty archives")
    drop_collection(config.mg_config, collection="queries_archives")


if __name__ == "__main__":
    demo_config = DemoAdminConfig()

    add_lomas_demo_data(demo_config)
