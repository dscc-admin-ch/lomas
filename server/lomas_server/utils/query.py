from collections.abc import Callable
from typing import Any

import httpx2
from pydantic import (
    HttpUrl,
)
from returns.converters import maybe_to_result
from returns.maybe import Maybe, Some
from returns.pipeline import flow
from returns.pointfree import bind, lash, map_
from returns.result import Failure, ResultE, Success, safe

from lomas_core.utils import url_append
from lomas_server.models.config import AdminConfig, DexAdminConfig


@safe
def get_config() -> AdminConfig:
    return AdminConfig()


@safe
def parse_if_ok(response: httpx2.Response) -> str | None:
    # Allow HTTP_204_NO_CONTENT
    if response.status_code == 204:
        return None
    return response.raise_for_status().json()


def recover_if_410(e: Exception, default: Any = None) -> ResultE:
    match e:
        case httpx2.HTTPStatusError():
            if e.response.status_code == 410:
                return Success(default)
        case _:
            pass
    return Failure(e)


def query_lomas(
    endpoint: str, verb: Callable[..., httpx2.Response], host: HttpUrl | None = None, **kwargs: dict[str, Any]
) -> ResultE[str | None]:
    return flow(
        maybe_to_result(Maybe.from_optional(host)),
        # get/parse our config from environment/files
        lash(lambda _: get_config().map(lambda config: config.server_service)),
        # build complete API endpoint
        map_(lambda host: url_append(host, endpoint)),
        # do the request while capturing Errors
        bind(lambda url: safe(verb)(str(url), **kwargs)),
        # ensure HTTP 200 and parse
        bind(parse_if_ok),
    )


def call_if_dex(task: Callable[[DexAdminConfig], ResultE]) -> ResultE[Maybe[ResultE]]:
    """Gets the Dex config and if it exists, passes it to the provided task.

    Args:
        task (Callable[[DexAdminConfig], ResultE]): The task to run.

    Returns:
        ResultE[Maybe[ResultE]]: An Failure if the task returns a failure or the config cannot be read.
    """

    def unwrap_Failure(res: ResultE[Maybe[ResultE]]) -> ResultE[Maybe[ResultE]]:
        match res:
            case Success(Some(Failure(e))):
                return Failure(e)
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
