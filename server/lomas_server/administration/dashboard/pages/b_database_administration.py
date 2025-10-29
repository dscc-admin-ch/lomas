from pathlib import Path

import streamlit as st
import yaml

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import DatasetsCollection
from lomas_core.models.constants import PrivateDatabaseType
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.admin_database.constants import BudgetDBKey
from lomas_server.administration.keycloak_admin import get_kc_user_client_secret, set_kc_user_client_secret
from lomas_server.administration.lomas_admin import (
    add_lomas_user,
    add_lomas_user_with_budget,
    add_lomas_users_via_yaml,
    del_lomas_user,
    drop_lomas_collection,
)
from lomas_server.constants import DELTA_LIMIT, EPSILON_LIMIT
from lomas_server.models.config import AdminConfig

EPSILON_STEP = 0.01
DELTA_STEP = 0.00001


def get_list_of_datasets_from_user(db: AdminDatabase, username: str) -> list:
    """List of datasets User has access to."""
    return list(
        map(
            lambda ds: ds.dataset_name,
            next(user for user in db.users() if user.id.name == username).datasets_list,
        )
    )


def warning_field_missing() -> None:
    """Writes warning that some fields are missing."""
    st.warning("Please fill all fields.")


###############################################################################
# BACKEND
###############################################################################
try:
    if "dashboard_config" not in st.session_state:
        # Store dashboard config
        st.session_state["dashboard_config"] = AdminConfig()
except InternalServerException as e:
    st.error(f"Failed to load server or dashboard config. Initial exception: {e}")


def sync_datasets() -> None:
    """Refresh the list of datasets."""
    config = st.session_state.get("dashboard_config", AdminConfig())
    st.session_state["list_datasets"] = list(map(lambda ds: ds.dataset_name, config.database.datasets()))


def sync_users() -> None:
    """Refresh the list of users."""
    config = st.session_state.get("dashboard_config", AdminConfig())
    st.session_state["list_users"] = list(map(lambda u: u.id.name, config.database.users()))


if "list_users" not in st.session_state:
    sync_users()

if "list_datasets" not in st.session_state:
    sync_datasets()


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.title("Admin Database Management")

user_tab, dataset_tab, content_tab, deletion_tab = st.tabs(
    [
        ":technologist: User Management",
        ":file_cabinet: Dataset Management",
        ":eyes: View Database Content",
        ":wastebasket: Delete Content (:red[DANGEROUS])",
    ]
)

with user_tab:
    st.subheader("Add user")
    au_1, au_2, au_3 = st.columns(3)
    with au_1:
        au_username = st.text_input("Username (add user)", value="", key="au_username_key")
    with au_2:
        au_email = st.text_input("Email (add user)", value="", key="au_email_key")
    with au_3:
        au_client_secret = st.text_input(
            "Client secret (add user), can be left empty.",
            value="",
            key="au_client_secret_key",
            type="password",
        )
    if st.button("Add user", key="add_user_button"):
        if au_username in st.session_state.list_users:
            st.warning(f"User {au_username} is already in the database.")
        elif au_username and au_email:
            add_lomas_user(st.session_state.dashboard_config, au_username, au_email, au_client_secret)
            sync_users()
            st.write(f"User {au_username} was added.")
        else:
            warning_field_missing()

    st.subheader("Add user with budget")
    auwb_1, auwb_2, auwb_3 = st.columns(3)
    with auwb_1:
        auwb_username = st.text_input("Username (add user with budget)", key="auwb_username")
        if auwb_username in st.session_state.list_users:
            st.warning(f"User {auwb_username} is already in the database.")
    with auwb_2:
        auwb_email = st.text_input("Email (add user)", value="", key="auwb_email_key")
    with auwb_3:
        auwb_client_secret = st.text_input(
            "Client secret (add user), can be left empty.",
            value="",
            key="auwb_client_secret_key",
            type="password",
        )

    auwb_4, auwb_5, auwb_6 = st.columns(3)
    with auwb_4:
        auwb_dataset = st.selectbox(
            "Dataset (add user with budget)",
            st.session_state.list_datasets,
            key="dataset of add user with budget",
        )
    with auwb_5:
        auwb_epsilon = st.number_input(
            "Epsilon (add user with budget)",
            min_value=0.0,
            max_value=EPSILON_LIMIT,
            step=EPSILON_STEP,
            format="%f",
            key="auwb_epsilon",
        )
    with auwb_6:
        auwb_delta = st.number_input(
            "Delta (add user with budget)",
            min_value=0.0,
            max_value=DELTA_LIMIT,
            step=DELTA_STEP,
            format="%f",
            key="auwb_delta",
        )

    if st.button("Add user with dataset", key="add_user_with_budget"):
        if auwb_username and auwb_email and auwb_dataset and auwb_epsilon and auwb_delta:
            add_lomas_user_with_budget(
                st.session_state.dashboard_config,
                auwb_username,
                auwb_email,
                auwb_dataset,
                auwb_epsilon,
                auwb_delta,
                auwb_client_secret,
            )
            sync_users()
            st.write(f"User {auwb_username} was added with dataset {auwb_dataset}.")
        else:
            warning_field_missing()

    st.subheader("Add dataset to user")
    adtu_1, adtu_2, adtu_3, adtu_4 = st.columns(4)
    with adtu_1:
        adtu_username = st.selectbox(
            "Username (add dataset to user)",
            st.session_state.list_users,
            key="username of add dataset to user",
        )
    with adtu_2:
        if adtu_username:
            adtu_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.dashboard_config.database, adtu_username
            )
            adtu_dataset_available = [
                dataset
                for dataset in st.session_state.list_datasets
                if dataset not in adtu_datasets_from_user
            ]
        else:
            adtu_dataset_available = st.session_state.list_datasets
        adtu_dataset = st.selectbox(
            "Dataset (add dataset to user)",
            adtu_dataset_available,
            key="dataset of add dataset to user",
        )
    with adtu_3:
        adtu_epsilon = st.number_input(
            "Epsilon (add dataset to user)",
            min_value=0.0,
            max_value=EPSILON_LIMIT,
            step=EPSILON_STEP,
            format="%f",
            key="adtu_epsilon",
        )
    with adtu_4:
        adtu_delta = st.number_input(
            "Delta (add dataset to user)",
            min_value=0.0,
            max_value=DELTA_LIMIT,
            step=DELTA_STEP,
            format="%f",
            key="adtu_delta",
        )

    if st.button("Add dataset to user", key="add_dataset_to_user"):
        if adtu_username and adtu_dataset and adtu_epsilon and adtu_delta:
            st.session_state.dashboard_config.database.add_dataset_to_user(
                adtu_username,
                adtu_dataset,
                adtu_epsilon,
                adtu_delta,
            )
            st.write(
                f"Dataset {adtu_dataset} was added to user {adtu_username}"
                + f" with epsilon = {adtu_epsilon} and delta = {adtu_delta}"
            )
        else:
            warning_field_missing()

    st.subheader("Set user client secret")
    sucs_1, sucs_2 = st.columns(2)
    with sucs_1:
        sucs_username = st.selectbox(
            "Username (set user client_secret)",
            st.session_state.list_users,
            key="sucs_username",
        )
    with sucs_2:
        sucs_client_secret = st.text_input(
            "Client secret (set user client_secret)", key="sucs_client_secret", type="password"
        )

    if st.button("Set user client secret", key="set_user_client_secret"):
        if sucs_username and sucs_client_secret:
            set_kc_user_client_secret(
                st.session_state.dashboard_config.kc_config, sucs_username, sucs_client_secret
            )
            st.write(f"Set new client secret for user {sucs_username}")
        else:
            warning_field_missing()

    st.subheader("Modify user epsilon")
    sue_1, sue_2, sue_3 = st.columns(3)
    with sue_1:
        sue_username = st.selectbox(
            "Username (modify user epsilon)",
            st.session_state.list_users,
            key="username of modify user epsilon",
        )
    with sue_2:
        if sue_username:
            sue_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.dashboard_config.database, sue_username
            )
        else:
            sue_datasets_from_user = st.session_state.list_datasets
        sue_dataset = st.selectbox(
            "Dataset (modify user epsilon)",
            sue_datasets_from_user,
            key="dataset of modify user epsilon",
        )
    with sue_3:
        sue_epsilon = st.number_input(
            "Epsilon value (modify user epsilon)",
            min_value=0.0,
            max_value=EPSILON_LIMIT,
            step=EPSILON_STEP,
            format="%f",
            key="sue_epsilon",
        )

    if st.button("Modify user epsilon", key="modify_user_epsilon"):
        if sue_username and sue_dataset and sue_epsilon:
            st.session_state.dashboard_config.database.update_epsilon_or_delta(
                sue_username, sue_dataset, BudgetDBKey.EPSILON_INIT, sue_epsilon
            )
            st.write(
                f"User {sue_username} on dataset {sue_dataset} "
                + f"initial epsilon value was modified to {sue_epsilon}"
            )
        else:
            warning_field_missing()

    st.subheader("Modify user delta")
    sud_1, sud_2, sud_3 = st.columns(3)
    with sud_1:
        sud_username = st.selectbox(
            "Username (modify user delta)",
            st.session_state.list_users,
            key="username of modify user delta",
        )
    with sud_2:
        if sud_username:
            sud_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.dashboard_config.database, sud_username
            )
        else:
            sud_datasets_from_user = st.session_state.list_datasets
        sud_dataset = st.selectbox(
            "Dataset (modify user delta)",
            sud_datasets_from_user,
            key="dataset of modify user delta",
        )
    with sud_3:
        sud_delta = st.number_input(
            "Delta value (modify user delta)",
            min_value=0.0,
            max_value=DELTA_LIMIT,
            step=DELTA_STEP,
            format="%f",
            key="sud_delta",
        )

    if st.button("Modify user delta", key="modify_user_delta"):
        if sud_username and sud_dataset and sud_delta:
            st.session_state.dashboard_config.database.update_epsilon_or_delta(
                sud_username,
                sud_dataset,
                BudgetDBKey.DELTA_INIT,
                sud_delta,
            )
            st.write(
                f"User {sud_username} on dataset {sud_dataset} "
                + f"initial delta value was modified to {sud_delta}"
            )
        else:
            warning_field_missing()

    st.subheader("Modify user may query")
    umq_1, umq_2 = st.columns(2)
    with umq_1:
        umq_username = st.selectbox(
            "Username (user may query)",
            st.session_state.list_users,
            key="username of user may query",
        )
    with umq_2:
        umq_may_query = st.selectbox("May query", (True, False), key="umq_may_query")
    if st.button("Modify user may query", key="m_u_m_q"):
        if umq_username:
            st.session_state.dashboard_config.database.set_may_user_query(umq_username, umq_may_query)
            st.write("User", umq_username, "may_query is now:", umq_may_query)
        else:
            warning_field_missing()

    st.subheader("Add many users via a yaml file")
    u_clean = st.toggle("Clean: recreate collection from scratch " + "(will delete all previous users)")
    u_uploaded_file = st.file_uploader(
        "Choose a YAML file for the user collection",
        accept_multiple_files=False,
    )

    if st.button("Add users"):
        if u_uploaded_file:
            st.write("Click to add users")
            user_collection = yaml.safe_load(u_uploaded_file)
            try:
                add_lomas_users_via_yaml(
                    st.session_state.dashboard_config,
                    user_collection,
                    u_clean,
                )
                sync_users()
                st.write("Users were added.")
            except ValueError as e:
                st.error(f"Failed to import collection because {e}")

            st.write(f"Users imported: {st.session_state.list_users}")
        else:
            warning_field_missing()

with dataset_tab:
    st.subheader("Add one dataset")
    ad_1, ad_2, ad_3 = st.columns(3)
    with ad_1:
        ad_dataset = st.text_input("Dataset name (add dataset)", None, key="ad_dataset")
        ad_dataset_warning = ad_dataset in st.session_state.list_datasets
        if ad_dataset_warning:
            st.warning(f"Dataset {ad_dataset} is already in the database.")

    with ad_2:
        ad_type = st.selectbox(
            "Dataset type (add dataset)",
            (PrivateDatabaseType.PATH, PrivateDatabaseType.S3),
            key="ad_type",
        )
    with ad_3:
        ad_meta_type = st.selectbox(
            "Metadata type (add dataset)",
            (PrivateDatabaseType.PATH, PrivateDatabaseType.S3),
            key="ad_meta_type",
        )
    match ad_type:
        case PrivateDatabaseType.PATH:
            ad_path = st.text_input("Dataset path (add dataset)", None, key="ad_path")
        case PrivateDatabaseType.S3:
            ad_s3_1, ad_s3_2, ad_s3_3 = st.columns(3)
            with ad_s3_1:
                ad_s3_bucket = st.text_input("bucket (add dataset)", None, key="ad_s3_bucket")
            with ad_s3_2:
                ad_s3_key = st.text_input("key (add dataset)", None, key="ad_s3_key")
            with ad_s3_3:
                ad_s3_url = st.text_input("endpoint_url (add dataset)", None, key="ad_s3_url")

    match ad_meta_type:
        case PrivateDatabaseType.PATH:
            uploaded_metadata = st.file_uploader("Import your related metadata file", key="uploaded_metadata")
            ad_meta_path = None  # pylint: disable=invalid-name
            if uploaded_metadata is not None:
                ad_meta_path = Path("/tmp/metadata.yaml")
                ad_meta_path.write_bytes(uploaded_metadata.getbuffer())
                st.success(f"File {uploaded_metadata.name} uploaded successfully!")

        case PrivateDatabaseType.S3:
            (
                ad_meta_s3_1,
                ad_meta_s3_2,
                ad_meta_s3_3,
                ad_meta_s3_4,
                ad_meta_s3_5,
            ) = st.columns(5)
            with ad_meta_s3_1:
                ad_meta_s3_bucket = st.text_input(
                    "Metadata bucket (add dataset)", None, key="ad_meta_s3_bucket"
                )
            with ad_meta_s3_2:
                ad_meta_s3_key = st.text_input("Metadata key (add dataset)", None, key="ad_meta_s3_key")
            with ad_meta_s3_3:
                ad_meta_s3_url = st.text_input(
                    "Metadata endpoint_url (add dataset)", None, key="ad_meta_s3_url"
                )
            with ad_meta_s3_4:
                ad_meta_s3_kid = st.text_input(
                    "Metadata access_key_id (add dataset)", None, key="ad_meta_s3_kid"
                )
            with ad_meta_s3_5:
                ad_meta_s3_sk = st.text_input("Metadata secret_key (add dataset)", None, key="ad_meta_s3_sk")

    keyword_args = {}
    DATASET_READY = False
    METADATA_READY = False

    if ad_type == PrivateDatabaseType.PATH and ad_path:
        keyword_args["dataset_path"] = ad_path
        DATASET_READY = True
    elif ad_type == PrivateDatabaseType.S3 and ad_s3_bucket and ad_s3_key and ad_s3_url:
        keyword_args["bucket"] = ad_s3_bucket
        keyword_args["key"] = ad_s3_key
        keyword_args["endpoint_url"] = ad_s3_url
        DATASET_READY = True
    elif ad_dataset is not None:
        st.write("Please, fill all empty fields for dataset.")

    if ad_meta_type == PrivateDatabaseType.PATH and ad_meta_path:
        keyword_args["metadata_path"] = str(ad_meta_path)
        METADATA_READY = True
    elif ad_meta_type == PrivateDatabaseType.S3 and all(
        (ad_meta_s3_bucket, ad_meta_s3_key, ad_meta_s3_url, ad_meta_s3_kid, ad_meta_s3_sk)
    ):
        keyword_args["metadata_bucket"] = ad_meta_s3_bucket
        keyword_args["metadata_key"] = ad_meta_s3_key
        keyword_args["metadata_endpoint_url"] = ad_meta_s3_url
        keyword_args["metadata_access_key_id"] = ad_meta_s3_kid
        keyword_args["metadata_secret_access_key"] = ad_meta_s3_sk
        METADATA_READY = True
    elif ad_dataset is not None:
        st.write("Please, fill all empty fields for the metadata.")

    if st.button(
        f"Add {ad_type} dataset with {ad_meta_type} metadata",
        key="add_dataset_with_metadata",
    ):
        if DATASET_READY and METADATA_READY and not ad_dataset_warning:
            try:
                st.session_state.dashboard_config.database.add_dataset(
                    ad_dataset,
                    ad_type,
                    ad_meta_type,
                    **keyword_args,
                )
            except ValueError as e:
                st.error(f"Failed to add dataset because {e}")

            DATASET_READY = False
            METADATA_READY = False
            sync_datasets()
            st.write("Dataset", ad_dataset, "was added.")
        else:
            warning_field_missing()

    st.subheader("Add many datasets via a yaml file")
    d_clean = st.toggle("Clean: will delete all previous datasets", key="d_clean")
    dataset_collection = st.file_uploader(
        "Select a YAML file for the dataset collection",
        type="yaml",
        accept_multiple_files=False,
    )

    if st.button("Add datasets", key="Add datasets"):
        if dataset_collection:
            st.write("Click to add datasets")
            dataset_collection = DatasetsCollection(**yaml.safe_load(dataset_collection)).datasets
            st.session_state.database.load_dataset_collection(dataset_collection)
            sync_datasets()
            st.write(f"Datasets imported: {st.session_state.list_datasets}")
        else:
            warning_field_missing()

with content_tab:
    st.subheader("Show one element")
    elem_users, elem_archives = st.columns(2)
    with elem_users:
        user_selected = st.selectbox(
            "User to show",
            st.session_state.list_users,
            key="username of user to show",
        )
        if st.button(f"Displaying information of: {user_selected}", key="content_user_display"):
            user_to_show = next(
                filter(
                    lambda u: u.id.name == user_selected, st.session_state.dashboard_config.database.users()
                )
            )
            st.write(user_to_show.model_dump())

    with elem_archives:
        user_archives_selected = st.selectbox(
            "Archives from user",
            st.session_state.list_users,
            key="username of archives from user",
        )
        if st.button(
            f"Displaying previous queries of: {user_archives_selected}",
            key="content_user_archive_display",
        ):
            user_archives_to_show = st.session_state.dashboard_config.database.get_archives_of_user(
                user_archives_selected
            )
            st.write(user_archives_to_show)

    user_client_secret_selected = st.selectbox(
        "Client secret for user", st.session_state.list_users, key="user_to_show_client_secret"
    )
    if st.button(
        f"Display client secret for user: {user_client_secret_selected}",
        key="user_to_show_client_secret_display",
    ):
        user_client_secret = get_kc_user_client_secret(
            st.session_state.dashboard_config.kc_config, user_client_secret_selected
        )
        st.write(f"Client secret for user {user_client_secret_selected}:", user_client_secret)

    elem_datasets, elem_metadata = st.columns(2)
    with elem_datasets:
        dataset_selected = st.selectbox(
            "Dataset to show",
            st.session_state.list_datasets,
            key="dataset_to_show",
        )
        if st.button(f"Displaying dataset: {dataset_selected}", key="content_dataset_display"):
            dataset_to_show = st.session_state.dashboard_config.database.get_dataset(dataset_selected)
            st.write(dataset_to_show)

    with elem_metadata:
        metadata_selected = st.selectbox(
            "Metadata to show from dataset",
            st.session_state.list_datasets,
            key="metadata_of_dataset_to_show",
        )
        if st.button(
            f"Displaying metadata of: {metadata_selected}",
            key="content_metadata_dataset_display",
        ):
            metadata_to_show = st.session_state.dashboard_config.database.get_dataset_metadata(
                metadata_selected
            )
            st.write(metadata_to_show)

    st.subheader("Show full collection")
    col_users, col_datasets, col_metadata, col_archives = st.columns(4)
    with col_users:
        if st.button("Show all users", key="content_show_all_users"):
            users = st.session_state.dashboard_config.database.get_collection("users")
            st.write(users)
    with col_datasets:
        if st.button("Show all datasets", key="content_show_all_datasets"):
            datasets = st.session_state.dashboard_config.database.get_collection("datasets")
            st.write(datasets)
    with col_metadata:
        if st.button("Show all metadata", key="content_show_all_metadata"):
            metadatas = st.session_state.dashboard_config.database.get_collection("metadatas")
            st.write(metadatas)
    with col_archives:
        if st.button("Show archives", key="content_show_archives"):
            archives = st.session_state.dashboard_config.database.get_collection("queries_archives")
            st.write(archives)


with deletion_tab:
    _, center, _ = st.columns(3)
    with center:
        st.markdown(":warning: :red[**Danger Zone: deleting is final**]")

    st.subheader("Delete one element")
    st.markdown("**Delete one user**")
    du_username = st.selectbox(
        "Username (delete user)",
        st.session_state.list_users,
        key="du_username",
    )

    if st.button(label=f"Delete user {du_username} from the list of users.", key="delete_user"):
        if du_username:
            del_lomas_user(st.session_state.dashboard_config, du_username)
            sync_users()
            st.write(f"User {du_username} was deleted.")
        else:
            warning_field_missing()

    st.markdown("**Remove dataset from user**")
    rdtu_1, rdtu_2 = st.columns(2)
    with rdtu_1:
        rdtu_user = st.selectbox(
            "Username (remove dataset from user)",
            st.session_state.list_users,
            key="rdtu_user",
        )
    with rdtu_2:
        if rdtu_user:
            rdtu_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.dashboard_config.database, rdtu_user
            )
        else:
            rdtu_datasets_from_user = st.session_state.list_datasets
        rdtu_dataset = st.selectbox(
            "Dataset (remove dataset from user)",
            rdtu_datasets_from_user,
            key="rdtu_dataset",
        )

    if st.button(
        label=f"Remove dataset {rdtu_dataset} from user {rdtu_user}.",
        key="delete_dataset_from_user",
    ):
        if rdtu_user and rdtu_dataset:
            st.session_state.dashboard_config.database.del_dataset_to_user(rdtu_user, rdtu_dataset)
            sync_datasets()
            st.write(f"Dataset {rdtu_dataset} was removed from user {rdtu_user}.")
        else:
            warning_field_missing()

    st.markdown("**Remove dataset and it's associated metadata**")
    rd_dataset = st.selectbox(
        "Dataset (remove dataset)",
        st.session_state.list_datasets,
        key="rd_dataset",
    )

    if st.button(
        label=f"Delete dataset {rd_dataset} from the list of datasets.",
        key="delete_dataset_and_metadata",
    ):
        if rd_dataset:
            st.session_state.dashboard_config.database.del_dataset(rd_dataset)
            sync_datasets()
            st.write(f"Dataset {rd_dataset} was deleted.")
        else:
            warning_field_missing()

    st.subheader("Delete full collection")
    d_col_users, d_col_datasets, d_col_metadata, d_col_archives = st.columns(4)

    with d_col_users:
        if st.button("Delete all users", key="delete_all_users"):
            drop_lomas_collection(st.session_state.dashboard_config, "users")
            sync_users()
            st.write("Users were all deleted.")

    with d_col_datasets:
        if st.button(
            "Delete all datasets",
            on_click=drop_lomas_collection,
            args=(st.session_state.dashboard_config, "datasets"),
            key="delete_all_datasets",
        ):
            sync_datasets()
            st.write("Datasets were all deleted.")

    with d_col_metadata:
        if st.button(
            "Delete all metadata",
            on_click=drop_lomas_collection,
            args=(st.session_state.dashboard_config, "metadata"),
            key="delete_all_metadata",
        ):
            st.write("Metadata were all deleted.")

    with d_col_archives:
        if st.button(
            "Delete all archives",
            on_click=drop_lomas_collection,
            args=(st.session_state.dashboard_config, "archives"),
            key="delete_all_archives",
        ):
            st.write("Archives were all deleted.")
