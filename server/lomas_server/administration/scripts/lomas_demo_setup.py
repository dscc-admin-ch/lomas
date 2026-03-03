from pathlib import Path

import httpx
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from rich.pretty import pprint

from lomas_server.admin_database.constants import TopDBKey as TK
from lomas_server.administration.dashboard.utils import query_lomas
from lomas_server.administration.dex.dex_admin import add_dex_users_via_yaml
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

    user_yaml: Path = Field(default=Path("../data/collections/user_collection.yaml"))
    dataset_yaml: Path = Field(default=Path("../data/collections/dataset_collection.yaml"))
    bootstrap: str


def add_lomas_demo_data(config: DemoAdminConfig) -> None:
    """
    Adds the demo data to the admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    pprint("Creating user collection from Config")
    pprint(config)

    query_lomas(
        "/usersfile",
        httpx.post,
        json={"clean": True},
        files={"file": config.user_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )
    if config.dex_config is not None:
        add_dex_users_via_yaml(
            config.dex_config,
            yaml_file=config.user_yaml,
            clean=False,
            overwrite=True,
        )

    pprint("Creating datasets and metadata collection")
    query_lomas(
        "/dataset/bulk",
        httpx.post,
        json={"clean": True},
        files={"file": config.dataset_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    pprint("Empty archives")
    query_lomas(
        f"/collections/{TK.ARCHIVE}",
        httpx.delete,
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )


def lomas_demo_setup() -> None:
    """Script for setting up demo users and dataset."""
    demo_config = DemoAdminConfig()
    add_lomas_demo_data(demo_config)


if __name__ == "__main__":
    lomas_demo_setup()
