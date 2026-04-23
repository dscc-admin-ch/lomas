import posix as Status
from functools import partial
from pathlib import Path

import httpx
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from returns.converters import flatten, maybe_to_result
from returns.io import IOFailure, IOResultE, IOSuccess
from returns.iterables import Fold
from returns.maybe import Maybe
from returns.pipeline import flow
from returns.pointfree import map_
from returns.result import Failure
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


def add_lomas_demo_data(config: DemoAdminConfig) -> IOResultE:
    """
    Adds the demo data to the admindb as well as the keycloak instance if required.

    Meant to be used in the develop mode of the service or for testing

    Args:
        config (AdminConfig): The administration config.
    """
    pprint("Creating user collection from Config")
    pprint(config)

    add_users: IOResultE = query_lomas(
        "/usersfile",
        httpx.post,
        json={"clean": True},
        files={"file": config.user_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    add_dex_users: IOResultE = flow(
        config.dex_config,  # DexAdminConfig | None
        Maybe.from_optional,  # Maybe[DexAdminConfig]
        map_(  # Maybe[IOResultE]
            partial(  # DexAdminConfig -> IOResultE
                add_dex_users_via_yaml, yaml_file=config.user_yaml, clean=False, overwrite=True
            )
        ),
        (lambda m: m.value_or(Maybe.from_value(IOSuccess("No Dex config")))),  # No dex config is not an issue
        maybe_to_result,  # Result[IOResultE]
        flatten,  # IOResultE
    )

    pprint("Creating datasets and metadata collection")
    add_datasets: IOResultE = query_lomas(
        "/dataset/bulk",
        httpx.post,
        json={"clean": True},
        files={"file": config.dataset_yaml.open(mode="rb")},
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    pprint("Empty archives")
    delete_archives: IOResultE = query_lomas(
        f"/collections/{TK.ARCHIVE}",
        httpx.delete,
        headers={"Authorization": f"Bearer {config.bootstrap}"},
    )

    return Fold.collect([add_users, add_dex_users, add_datasets, delete_archives], IOSuccess(()))


def lomas_demo_setup() -> int:
    """Script for setting up demo users and dataset.

    Returns:
        int: the return code used by sys.exit (0 for success 1 or other for failure)
    """
    demo_config = DemoAdminConfig()
    match add_lomas_demo_data(demo_config):
        case IOSuccess(_):
            return Status.EX_OK
        case IOFailure(Failure(e)):
            return e
    return Status.EX_IOERR


if __name__ == "__main__":
    lomas_demo_setup()
