import posix as Status
from functools import partial
from pathlib import Path

import httpx2
from pydantic import Field
from pydantic_settings import CliApp, SettingsConfigDict
from returns.functions import raise_exception
from returns.maybe import Maybe
from returns.pipeline import flow
from returns.pointfree import bind, map_
from returns.result import Failure, ResultE, Success
from rich.pretty import pprint

from lomas_server.admin_database.constants import TopDBKey as TK
from lomas_server.administration.dex.dex_admin import add_dex_users_via_yaml
from lomas_server.models.config import AdminConfig
from lomas_server.utils.query import query_lomas


class DemoAdminConfig(AdminConfig):
    """Extension of Admin config for demo setup."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_admin_",
        env_file=".env.lomas_admin",
        env_nested_delimiter="__",
        case_sensitive=False,
        cli_kebab_case=True,
        cli_avoid_json=True,
        cli_implicit_flags="toggle",
        cli_shortcuts={
            "external-url": "s",
            "user-yaml": "u",
            "dataset-yaml": "d",
        },
    )

    user_yaml: Path = Field(default=Path("../data/collections/user_collection.yaml"))
    dataset_yaml: Path = Field(default=Path("../data/collections/dataset_collection.yaml"))
    bootstrap: str = Field(description="Bootstrap secret to bypass auth during initial setup")


def add_lomas_demo_data(config: DemoAdminConfig) -> ResultE:
    """
    Adds the demo data to the admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    pprint(config)

    add_users: ResultE = query_lomas(
        "/usersfile",
        httpx2.post,
        data={"clean": True, "overwrite": False},
        files={"file": config.user_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    add_dex_users: ResultE = flow(
        config.dex_config,  # DexAdminConfig | None
        Maybe.from_optional,  # Maybe[DexAdminConfig]
        map_(  # Maybe[ResultE]
            partial(  # DexAdminConfig -> ResultE
                add_dex_users_via_yaml, yaml_file=config.user_yaml, clean=False, overwrite=True
            )
        ),
    ).value_or(Success("No Dex config"))

    add_datasets: ResultE = query_lomas(
        "/dataset/bulk",
        httpx2.post,
        data={"clean": True},
        files={"file": config.dataset_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    delete_archives: ResultE = query_lomas(
        f"/collections/{TK.ARCHIVE}",
        httpx2.delete,
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    result = flow(
        Success(()),
        map_(lambda _: pprint("Creating user collection from Config")),
        bind(lambda _: add_users),
        map_(lambda _: pprint("Adding Dex Users")),
        bind(lambda _: add_dex_users),
        map_(lambda _: pprint("Creating datasets and metadata collection")),
        bind(lambda _: add_datasets),
        map_(lambda _: pprint("Empty archives")),
        bind(lambda _: delete_archives),
    )
    return result


def lomas_demo_setup(demo_config: DemoAdminConfig | None = None) -> int:
    """Script for setting up demo users and dataset.

    Returns:
        int: the return code used by sys.exit (0 for success 1 or other for failure)
    """
    if demo_config is None:
        demo_config = DemoAdminConfig()

    match add_lomas_demo_data(demo_config):
        case Success(_):
            return Status.EX_OK
        case Failure(e):
            raise_exception(e)
    return Status.EX_IOERR


def run() -> int:
    demo_config = CliApp.run(DemoAdminConfig)
    return lomas_demo_setup(demo_config)


if __name__ == "__main__":
    run()
