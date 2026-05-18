from functools import partial
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
import yaml
from returns.converters import maybe_to_result
from returns.io import IO, IOFailure, IOResultE, IOSuccess
from returns.iterables import Fold
from returns.maybe import Maybe, Some
from returns.pipeline import flow
from returns.pointfree import alt, bind, bind_result, lash, map_
from returns.result import Failure, ResultE, Success

from lomas_core.models.collections import User, UserCollection, UserId
from lomas_core.models.constants import PrivateDatabaseType
from lomas_core.models.requests import LomasBudgetRequest, LomasRequestModel
from lomas_server.admin_database.constants import TopDBKey as TK
from lomas_server.administration.dashboard.utils import (
    call_if_dex,
    confirm_delete,
    ensure_user_has_datasets,
    find_user,
    get_config,
    get_datasets,
    get_user_df,
    get_users,
    list_users,
    query_lomas_auth,
    recover_if_410,
)
from lomas_server.administration.dex.dex_admin import (
    add_dex_user,
    add_dex_users,
    del_all_dex_users,
    del_dex_user,
)

EPSILON_LIMIT = 500.0
EPSILON_STEP = 0.01

DELTA_LIMIT = 0.5
DELTA_STEP = 0.00001


st.title("Bootstrap permissions")

bootstrap_exists = flow(
    query_lomas_auth("/bootstrap", httpx.get),
    lash(lambda e: recover_if_410(e, default=False)),
    alt(lambda e: st.error(f"Error while fetching bootstrap state: {e}")),
    map_(lambda e: True if e is None else False),  # Define bootstrap_exists
)

delete_bootstrap = False
match bootstrap_exists:
    case IOFailure():
        pass  # case handled above
    case IOSuccess(Success(True)):
        with st.container(horizontal_alignment="center"):
            delete_bootstrap = st.button(
                "Delete bootstrap permissions", type="primary", key="del_bootstrap_button"
            )
    case IOSuccess(Success(False)):
        st.success("Bootstrap permissions already removed")

if delete_bootstrap:
    confirm_delete(
        "Delete bootstrap permissions permanently?",
        lambda: query_lomas_auth("/bootstrap", httpx.delete),
        "Bootstrap has been deleted",
    )

st.divider()
st.title("Users")

row_selector = flow(
    get_user_df(),
    # Render error (if any)
    alt(lambda e: st.error(f"Error while fetching User dataframe: {e}")),
    # build the dataframe
    map_(
        lambda df: st.dataframe(
            df.drop("dsofuser", axis=1),  # drop unserializa:eable column (hidding it still spam errors)
            on_select="rerun",
            selection_mode="single-row",
        )
    ),
)

selected_row: IOResultE[pd.DataFrame] = flow(
    row_selector,
    # transform empty row into a Result
    bind_result(
        lambda event: (
            Success(event.selection.rows[0])
            if len(event.selection.rows) > 0
            else Failure(IndexError("No row selected"))
        )
    ),
    # extract the row (safeguarding user_df possible errors)
    bind(lambda idx: get_user_df().map(lambda df: df.iloc[idx])),
)


budget_editor = flow(
    selected_row,
    # allow safe \.dsofuser
    bind_result(ensure_user_has_datasets),
    # build the editor
    map_(
        lambda row: st.data_editor(
            row.dsofuser,
            column_config={
                "dataset_name": st.column_config.TextColumn(label="Dataset", disabled=True),
                "initial_epsilon": st.column_config.NumberColumn(
                    label="ε",
                    required=True,
                    min_value=0.0,
                    max_value=EPSILON_LIMIT,
                    step=EPSILON_STEP,
                    format="%f",
                ),
                "initial_delta": st.column_config.NumberColumn(
                    label="δ",
                    required=True,
                    min_value=0.0,
                    max_value=DELTA_LIMIT,
                    step=DELTA_STEP,
                    format="%f",
                ),
                "total_spent_epsilon": st.column_config.NumberColumn(label="spent ε", disabled=True),
                "total_spent_delta": st.column_config.NumberColumn(label="spent δ", disabled=True),
            },
            hide_index=True,
        )
    ),
)


def update_budget(row: IOResultE[pd.DataFrame], edited_row: pd.DataFrame) -> None:
    user_select = row.Name
    diff = edited_row.set_index("dataset_name") - row.dsofuser.set_index("dataset_name")
    for t in diff.itertuples():
        if t.initial_epsilon != 0 or t.initial_delta != 0:
            new_val = edited_row.set_index("dataset_name").loc[t.Index]
            budgetReq = LomasBudgetRequest(
                dataset_name=t.Index,
                epsilon=new_val.initial_epsilon,
                delta=new_val.initial_delta,
            )
            query_lomas_auth(
                f"/users/{user_select}/dataset/budget",
                httpx.patch,
                json=budgetReq.model_dump(),
            )

            st.success(
                f"Updated ε, δ of {user_select} on dataset {budgetReq.dataset_name} to {budgetReq.epsilon}, {budgetReq.delta}"
            )


update_budget_from_row = flow(
    selected_row, bind_result(ensure_user_has_datasets), map_(lambda row: partial(update_budget, row))
)

budget_editor.apply(update_budget_from_row)


def ds_multi_select(row: IOResultE[pd.DataFrame], datasets_list: list[str]) -> None:
    user_select = row.Name
    remaining_ds = set(datasets_list) - set(row.datasets)
    with st.form("Add Dataset to User"):
        ds_multi_select_pill = st.pills(
            f"Add Dataset to {user_select}", options=remaining_ds, selection_mode="multi"
        )
        submit = st.form_submit_button()

    if submit:
        for selected in ds_multi_select_pill:
            query_lomas_auth(
                f"/users/{user_select}/dataset",
                httpx.patch,
                json=LomasRequestModel(dataset_name=selected).model_dump(),
            )
            st.toast(f":green[{selected} added to {user_select}]")


update_user_ds_from_row = flow(
    selected_row,
    map_(lambda row: partial(ds_multi_select, row)),
)

ds_user_editor = get_datasets().apply(update_user_ds_from_row)


def prev_query_btn(row: IOResultE[pd.DataFrame]) -> IOResultE[httpx.Response]:
    user_select = row.Name
    if st.button("Previous queries"):
        return query_lomas_auth(f"/users/{user_select}/archive", httpx.get)
    return IOFailure(None)


flow(
    selected_row,
    bind(prev_query_btn),
    map_(st.write),
)


def add_lomas_user(new_user: User) -> IOResultE:
    add_lomas_user_res: IOResultE = query_lomas_auth("/users", httpx.post, json=new_user.model_dump())

    add_dex_user_res: IOResultE = call_if_dex(  # We keep the Maybe so that we only add dex user if DexConfig
        partial(
            add_dex_user,
            user_name=new_user.id.name,
            user_email=new_user.id.email,
            user_password=new_user.id.client_secret,
        )
    )

    return Fold.collect([add_lomas_user_res, add_dex_user_res], IOSuccess("Success"))


def drop_lomas_collection(collection_name: str) -> IOResultE[httpx.Response]:
    return query_lomas_auth(f"/collections/{collection_name}", httpx.delete)


#############################
# GUI and user interactions #
#############################

st.subheader("Add user")
with st.form("Add user"):
    c1, c2, c3 = st.columns(3, vertical_alignment="center")
    with c1:
        au_username = st.text_input("Username", key="au_username_key")
    with c2:
        au_email = st.text_input("Email", key="au_email_key")
    with c3:
        get_dex_config = flow(get_config(), map_(lambda config: Maybe.from_optional(config.dex_config)))
        match get_dex_config:
            case IOFailure(_):
                pass
            case IOSuccess(Success(Maybe.empty)):
                st.write("Make sure the user exists at your ID provider!")
                au_password = None
            case IOSuccess(Success(Some(dex_config))):
                au_password = st.text_input(
                    "Password (can be empty)",
                    key="au_password",
                    type="password",
                )
    submit = st.form_submit_button()

if submit:
    if list_users().map(lambda usernames: au_username in usernames) == IO(True):
        st.warning(f"User {au_username} already in the database.")
    elif au_username and au_email:
        new_user = User(
            id=UserId(name=au_username, email=au_email, client_secret=au_password),
            may_query=False,
            datasets_list=[],
        )
        match add_lomas_user(new_user):
            case IOSuccess(_):
                st.success(f"User {au_username} added.")
            case IOFailure(fail):
                st.error(f"Failed to add {au_username}: {fail}")
    else:
        st.warning("Please fill all fields.")

# --------------------------------------

st.subheader("Bulk users import")

u_file = st.file_uploader("User collection (YAML)", type="yaml")
u_clean = st.toggle("Overwrite all current users & collection")

if u_file and st.button("Import"):
    query_lomas_auth("/usersfile", httpx.post, json={"clean": u_clean}, files={"file": u_file}).alt(
        lambda e: st.error(f"Failed to import collection because {e}")
    )

    # Reset cursor to start of file
    u_file.seek(0)

    add_dex_users_res: IOResultE = flow(
        call_if_dex(
            partial(
                add_dex_users,
                user_list=UserCollection(**yaml.safe_load(u_file)),
                clean=u_clean,
                overwrite=u_clean,  # TODO u_file does not resolve
            )
        ),  # IOResult
        alt(lambda e: st.error(f"Failed to create dex users because: {e}")),
    )

    st.success("Users imported")

    list_users().map(lambda usernames: [st.toast(f"(+) **{username}**") for username in usernames])


st.divider()
st.title("Datasets")

# TODO: How to nicely show dataset & metadata
ds_select_io = get_datasets().map(lambda ds_list: st.selectbox("Dataset", ds_list, key="select_ds_view"))
match ds_select_io:
    case IOFailure(Failure(e)):
        st.warning(f"fail to get dataset list: {e}")
    case IOSuccess(Success(None)):
        # No selections / no dataset avail. in lomas
        pass
    case IOSuccess(Success(ds_select)):
        cols = st.columns(2)
        with cols[0]:
            if st.button("Show", key="btn_show_ds"):
                match query_lomas_auth(f"/dataset/{ds_select}", httpx.get):
                    case IOSuccess(Success(dataset_info)):
                        st.json(dataset_info, expanded=2)
                    case IOFailure(fail):
                        st.error(f"{fail}")

        with cols[1]:
            if st.button("Metadata"):
                match query_lomas_auth(f"/dataset/{ds_select}/metadata", httpx.get):
                    case IOSuccess(Success(dataset_metadata)):
                        st.json(dataset_metadata, expanded=2)
                    case IOFailure(fail):
                        st.error(f"{fail}")

        st.divider()
        st.subheader(f"Add/Set metadata to {ds_select}")
        uploaded_metadata = st.file_uploader("File", key="uploaded_metadata_ds")
        if st.button("Submit", key="set_metadata", disabled=(uploaded_metadata is None)):
            match query_lomas_auth(
                f"/dataset/{ds_select}/metadata", httpx.patch, files={"file": uploaded_metadata}
            ):
                case IOSuccess(Success(_)):
                    st.success(f"Metadata added to {ds_select}.")
                case IOFailure(Failure(e)):
                    st.error(f"Failed to set metadata for {ds_select}:\n{e}")

# ------------------------

# FIXME: Single DS Add
st.subheader("Add dataset")
ad_dataset = st.text_input("Name", key="ad_dataset")
ad_dataset_warning: IO[bool] = get_datasets().map(lambda ds_list: ad_dataset in ds_list).value_or(False)
if ad_dataset_warning == IO(True):
    st.warning(f"{ad_dataset} already in Database.")

ad_path = st.text_input("Path", key="ad_path")

st.write("Metadata")
uploaded_metadata = st.file_uploader("File", key="uploaded_metadata")
ad_meta_path = None  # pylint: disable=invalid-name
if uploaded_metadata is not None:
    ad_meta_path = Path("/tmp/metadata.yaml")
    ad_meta_path.write_bytes(uploaded_metadata.getbuffer())

if st.button("Submit", key="add_dataset", disabled=(uploaded_metadata is None)) and ad_dataset_warning == IO(
    False
):
    match query_lomas_auth(
        "/dataset",
        httpx.post,
        json={
            "dataset_name": ad_dataset,
            "database_type": PrivateDatabaseType.PATH,
            "metadata_database_type": PrivateDatabaseType.PATH,
            "dataset_path": ad_path,
            "metadata_path": str(ad_meta_path),
        },
    ):
        case IOSuccess(Success(_)):
            st.success(f"Dataset {ad_dataset} added.")
        case IOFailure(Failure(e)):
            st.error(f"Failed to add dataset:\n{e}")

# --------------------------------------

st.subheader("Bulk datasets import")
dataset_collection = st.file_uploader("Dataset collection", type="yaml")
ds_clean = st.toggle("Overwrite all current datasets")

if st.button("Import", key="btn_import_ds", disabled=(not dataset_collection)):

    def on_success(arg: httpx.Response) -> IOResultE[list[str]]:
        st.success("Datasets imported")
        return get_datasets()

    def toast_ds(ds_list: list[str]) -> None:
        for ds in ds_list:
            st.toast(f"(+) **{ds}**")

    query_lomas_auth(
        "/dataset/bulk", httpx.post, json={"clean": ds_clean}, files={"file": dataset_collection}
    ).alt(lambda e: st.error(f"Failed to import datasets: {e}")).bind(on_success).map(toast_ds)


# ---------------------------------------------

st.divider()
st.title("Deletion")
_, center, _ = st.columns(3)
with center:
    st.markdown(":warning: :red[**Danger Zone: deleting is final**]")

col1, col2 = st.columns(2)
with col1:
    user_select_d: ResultE[str] = (
        list_users()
        .map(lambda usernames: st.selectbox("Username", usernames, key="user_select_d"))
        .map(Maybe.from_optional)
        .bind(maybe_to_result)
    )

with col2:
    ds_select_d: ResultE[str] = (
        user_select_d.bind(lambda username: get_users().bind(find_user(username)))
        .alt(st.warning)
        .map(lambda user_ds_list: [ds.dataset_name for ds in user_ds_list])
        .map(lambda user_ds_list: st.selectbox("Dataset", user_ds_list, key="ds_select_d"))
        .map(Maybe.from_optional)
        .bind(maybe_to_result)
    )


def delete_username_menu(username: str) -> None:
    st.subheader("**Delete User**")
    with st.form("Delete User"):
        submit = st.form_submit_button(f"delete {username}", type="primary")

    if submit:

        def delete_lomas_user() -> IOResultE:
            delete_lomas_user_res: IOResultE = query_lomas_auth(f"/users/{username}", httpx.delete)
            delete_dex_user_res: IOResultE = call_if_dex(
                partial(
                    del_dex_user,
                    user_name=username,
                )
            )
            return Fold.collect([delete_lomas_user_res, delete_dex_user_res], IOSuccess("User deleted"))

        confirm_delete(
            f"Are you sure you want to delete user **{username}**?",
            delete_lomas_user,
            f"**{username}** has been removed",
        )


user_select_d.map(delete_username_menu)


def delete_dataset_menu(username: str, ds_name: str) -> None:
    cols = st.columns(2)
    with cols[0]:
        st.subheader("**Remove dataset from user**")
        with st.form("Remove dataset from user"):
            submit = st.form_submit_button(f"Remove {ds_name} from {username}", type="primary")

        if submit:
            confirm_delete(
                f"Remove dataset **{ds_name}** from user **{username}**?",
                lambda: query_lomas_auth(
                    f"/users/{username}/dataset/del",
                    httpx.patch,
                    json=LomasRequestModel(dataset_name=ds_name).model_dump(),
                ),
                f"**{ds_name}** has been removed from user **{username}**",
            )


user_select_d.map(lambda username: ds_select_d.map(lambda ds_name: delete_dataset_menu(username, ds_name)))


def confirm_delete_dataset(ds_name: str) -> None:
    if st.button("Delete", key="btn_delete_ds"):
        confirm_delete(
            f"Delete dataset **{ds_name}** permanently?",
            lambda: query_lomas_auth(f"/dataset/{ds_name}", httpx.delete),
            f"**{ds_name}** has been removed.",
        )


st.subheader("**Delete dataset**")
ds_delete_select_io = flow(
    get_datasets(),
    map_(lambda ds_list: st.selectbox("Dataset", ds_list, key="select_ds_view_delete")),
    alt(lambda e: st.error(f"Fail to get dataset list: {e}")),
    map_(Maybe.from_optional),
    bind(maybe_to_result),
    map_(confirm_delete_dataset),
)

st.subheader("Delete full collection")
col1, col2, col3, col4 = st.columns(4, vertical_alignment="center")

with col1:
    if st.button("Delete all Users", type="primary", key="delete_all_users"):

        def del_all_lomas_users() -> IOResultE:
            delete_lomas_users_res: IOResultE = drop_lomas_collection(TK.USERS)
            delete_dex_users_res: IOResultE = call_if_dex(del_all_dex_users)
            return Fold.collect([delete_lomas_users_res, delete_dex_users_res], IOSuccess("Users deleted"))

        confirm_delete(
            "Are you sure you want to delete ALL USERS?",
            del_all_lomas_users,
            "All Users deleted.",
        )

with col2:
    if st.button("Delete all Datasets", type="primary", key="delete_all_datasets"):
        confirm_delete(
            "Are you sure you want to delete ALL DATASETS?",
            lambda: drop_lomas_collection(TK.DATASETS),
            "All Datasets deleted.",
        )

with col3:
    if st.button("Delete all Metadata", type="primary", key="delete_all_metadata"):
        confirm_delete(
            "Are you sure you want to delete ALL METADATA?",
            lambda: drop_lomas_collection(TK.METADATA),
            "All Metadata deleted.",
        )

with col4:
    if st.button("Delete all Archives", type="primary", key="delete_all_archives"):
        confirm_delete(
            "Are you sure you want to delete ALL ARCHIVES?",
            lambda: drop_lomas_collection(TK.ARCHIVE),
            "All Archives deleted.",
        )
