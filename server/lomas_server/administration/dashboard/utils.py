from collections.abc import Callable
from typing import Any

import httpx2
import pandas as pd
import streamlit as st
from returns.io import IO, IOFailure, IOResultE, IOSuccess, impure_safe
from returns.pipeline import flow
from returns.pointfree import alt, bind, cond, map_
from returns.result import Result, ResultE

from lomas_core.models.collections import DatasetOfUser, User
from lomas_server.utils.query import query_lomas


@st.dialog("Confirm deletion")
def confirm_delete(
    message: str, on_confirm: Callable[[], IOResultE[httpx2.Response]], success_message: str
) -> None:
    st.warning(message)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Yes", type="primary"):
            match on_confirm():
                case IOFailure(fail):
                    st.write(f"Operation failed: {fail}")
                case _:
                    st.write(success_message)

            st.rerun()

    with col2:
        if st.button("No"):
            st.rerun()


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
    verb: Callable[..., httpx2.Response],
    **kwargs: dict[str, Any],
) -> IOResultE[httpx2.Response]:
    return flow(
        get_access_token(),
        # transform a bare token into usable HTTP header
        map_(lambda token: {"Authorization": f"Bearer {token}"}),
        # Query lomas including auth header
        bind(lambda auth_header: query_lomas(endpoint, verb, headers=auth_header, **kwargs)),
    )


def get_datasets() -> IOResultE[list[str]]:
    """List all datasets available on the server."""
    return query_lomas_auth("/datasets", httpx2.get)


def get_users() -> IOResultE[list[User]]:
    """List all users available on the server."""
    return query_lomas_auth("/users", httpx2.get).map(
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
                    list(u.datasets.keys()),
                    pd.DataFrame([ds.model_dump() for ds in u.datasets.values()]),
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
        return next(list(u.datasets.values()) for u in users if u.id.name == username)

    return find_user_inner
