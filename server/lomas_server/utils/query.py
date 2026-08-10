from collections.abc import Callable
from typing import Any

import httpx2
from returns.io import IOFailure, IOResultE, IOSuccess, impure_safe
from returns.maybe import Maybe, Some
from returns.pipeline import flow
from returns.pointfree import bind, map_
from returns.result import Failure, Success

from lomas_core.utils import url_append
from lomas_server.models.config import AdminConfig, DexAdminConfig


@impure_safe
def get_config() -> AdminConfig:
    return AdminConfig()


@impure_safe
def parse_if_ok(response: httpx2.Response) -> str:
    return response.raise_for_status().json()


def recover_if_410(e: Exception, default: Any = None) -> IOResultE:
    match e:
        case httpx2.HTTPStatusError():
            if e.response.status_code == 410:
                return IOSuccess(default)
        case _:
            pass
    return IOFailure(e)


def query_lomas(
    endpoint: str, verb: Callable[..., httpx2.Response], **kwargs: dict[str, Any]
) -> IOResultE[httpx2.Response]:
    return flow(
        # get/parse our config from environment/files
        get_config(),
        # build complete API endpoint
        map_(lambda config: url_append(config.server_service, endpoint)),
        # do the request while capturing Errors
        bind(lambda url: impure_safe(verb)(str(url), **kwargs)),
        # ensure HTTP 200 and parse
        bind(parse_if_ok),
    )


def call_if_dex(task: Callable[[DexAdminConfig], IOResultE]) -> IOResultE[Maybe[IOResultE]]:
    """Gets the Dex config and if it exists, passes it to the provided task.

    Args:
        task (Callable[[DexAdminConfig], IOResultE]): The task to run.

    Returns:
        IOResultE[Maybe[IOResultE]]: An IOFailure if the task returns a failure or the config cannot be read.
    """

    def unwrap_Failure(res: IOResultE[Maybe[IOResultE]]) -> IOResultE[Maybe[IOResultE]]:
        match res:
            case IOSuccess(Success(Some(IOFailure(Failure(e))))):
                return IOFailure(e)
            case _:
                return res

    dex_config_res = flow(
        get_config(),
        map_(lambda config: Maybe.from_optional(config.dex_config)),
        map_(
            map_(task),
        ),
        unwrap_Failure,
    )

    return dex_config_res
