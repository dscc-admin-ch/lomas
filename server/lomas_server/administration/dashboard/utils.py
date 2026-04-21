from collections.abc import Callable
from typing import Any

import httpx
import pandas as pd
import streamlit as st
from pydantic import AnyUrl
from returns.io import IO, IOFailure, IOResultE, IOSuccess, impure_safe
from returns.pipeline import flow
from returns.pointfree import alt, bind, cond, map_
from returns.result import Result, ResultE

from lomas_core.models.collections import DatasetOfUser, User
from lomas_server.models.config import AdminConfig


def url_append(url: AnyUrl, path: str) -> AnyUrl:
    return url.build(
        scheme=url.scheme,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        path="/".join((url.path.rstrip("/"), path.lstrip("/"))).lstrip("/"),
        query=url.query,
        fragment=url.fragment,
    )


@st.cache_resource
@impure_safe
def get_config() -> AdminConfig:
    return AdminConfig()


@impure_safe
def parse_if_ok(response: httpx.Response) -> str:
    return response.raise_for_status().json()


def query_lomas(
    endpoint: str, verb: Callable[..., httpx.Response], **kwargs: dict[str, Any]
) -> IOResultE[httpx.Response]:
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


def get_access_token() -> IOResultE[str]:
    if not st.user.get("is_logged_in"):
        return IOFailure(ValueError("User is not logged"))

    return flow(
        IOSuccess("access"),
        # get the token safely
        bind(impure_safe(lambda key: st.user.tokens[key])),
        # rewrite this exception if any
        alt(lambda _: RuntimeError("Failed to get access token")),
    )


def query_lomas_auth(
    endpoint: str,
    verb: Callable[..., httpx.Response],
    **kwargs: dict[str, Any],
) -> IOResultE[httpx.Response]:
    return flow(
        get_access_token(),
        # transform a bare token into usable HTTP header
        map_(lambda token: {"Authorization": f"Bearer {token}"}),
        # Query lomas including auth header
        bind(lambda auth_header: query_lomas(endpoint, verb, headers=auth_header, **kwargs)),
    )


def get_datasets() -> IOResultE[list[str]]:
    """List all datasets available on the server."""
    return query_lomas_auth("/datasets", httpx.get)


def get_users() -> IOResultE[list[User]]:
    """List all users available on the server."""
    return query_lomas_auth("/users", httpx.get).map(
        lambda user_list: list(map(User.model_validate, user_list))
    )


def get_user_df() -> IOResultE[pd.DataFrame]:
    """Get all users into a displayable pandas dataframe."""
    # Specifying columns ever when users is [] allow subsequent .Name to be safe (and return [])
    columns = ["Name", "Email", "datasets", "dsofuser"]
    return get_users().map(
        lambda users: pd.DataFrame(
            columns=columns,
            data=[
                [
                    u.id.name,
                    u.id.email,
                    [ds.dataset_name for ds in u.datasets_list],
                    pd.DataFrame([ds.model_dump() for ds in u.datasets_list]),
                ]
                for u in users
            ],
        )
    )


def ensure_user_has_datasets(user_row: pd.DataFrame) -> ResultE[pd.DataFrame]:
    return cond(Result, user_row, ValueError("No dataset for user"))(not user_row.dsofuser.empty)


def list_users() -> IO[list[str]]:
    """List all usernames."""
    return get_user_df().map(lambda udf: udf.Name.tolist()).value_or([])


def find_user(username: str) -> Callable[[list[User]], list[DatasetOfUser]]:
    @impure_safe
    def find_user_inner(users: list[User]) -> list[DatasetOfUser]:
        return next(u.datasets_list for u in users if u.id.name == username)

    return find_user_inner
