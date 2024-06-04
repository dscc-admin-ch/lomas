# type: ignore
import streamlit as st
import yaml

from admin_database.utils import get_mongodb
from mongodb_admin import (
    add_user,
    add_user_with_budget,
    del_user,
    add_dataset_to_user,
    del_dataset_to_user,
    set_budget_field,
    set_may_query,
    show_user,
    add_users_via_yaml,
    add_dataset,
    add_datasets_via_yaml,
    del_dataset,
    drop_collection,
    get_list_of_users,
    get_list_of_datasets,
    get_list_of_datasets_from_user,
    show_archives_of_user,
    show_collection,
    show_dataset,
    show_metadata_of_dataset,
)
from constants import PrivateDatabaseType

###############################################################################
# BACKEND
###############################################################################
if "admin_db" not in st.session_state:
    st.session_state["admin_db"] = get_mongodb()

if "list_users" not in st.session_state:
    st.session_state["list_users"] = get_list_of_users(
        st.session_state.admin_db
    )

if "list_datasets" not in st.session_state:
    st.session_state["list_datasets"] = get_list_of_datasets(
        st.session_state.admin_db
    )

###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

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
    au_username = st.text_input("Username (add user)", value="", key=None)
    if au_username:
        st.write("Click to add user", au_username, "to the list of users.")
        if st.button(
            "Add user",
            on_click=add_user,
            args=(
                st.session_state.admin_db,
                au_username,
            ),
        ):
            st.session_state["list_users"] = get_list_of_users(
                st.session_state.admin_db
            )
            st.write(f"User {au_username} was added.")

    st.subheader("Add user with budget")
    auwb_1, auwb_2, auwb_3, auwb_4 = st.columns(4)
    with auwb_1:
        auwb_username = st.text_input("Username (add user with budget)", None)
    with auwb_2:
        auwb_dataset = st.selectbox(
            "Dataset (add user with budget)", st.session_state.list_datasets
        )
    with auwb_3:
        auwb_epsilon = st.number_input("Epsilon (add user with budget)", None)
    with auwb_4:
        auwb_delta = st.number_input("Delta (add user with budget)", None)
    if auwb_username and auwb_dataset and auwb_epsilon and auwb_delta:
        st.write("Click to add user", auwb_username, "to the list of users.")
        if st.button(
            "Add user with dataset",
            on_click=add_user_with_budget,
            args=(
                st.session_state.admin_db,
                auwb_username,
                auwb_dataset,
                auwb_epsilon,
                auwb_delta,
            ),
        ):
            st.session_state["list_users"] = get_list_of_users(
                st.session_state.admin_db
            )
            st.write(
                f"User {auwb_username} was added with dataset {auwb_dataset}."
            )

    st.subheader("Add dataset to user")
    adtu_1, adtu_2, adtu_3, adtu_4 = st.columns(4)
    with adtu_1:
        adtu_username = st.selectbox(
            "Username (add dataset to user)", st.session_state.list_users
        )
    with adtu_2:
        if adtu_username:
            adtu_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.admin_db, adtu_username
            )
            adtu_dataset_available = [
                dataset
                for dataset in st.session_state.list_datasets
                if dataset not in adtu_datasets_from_user
            ]
        else:
            adtu_dataset_available = st.session_state.list_datasets
        adtu_dataset = st.selectbox(
            "Dataset (add dataset to user)", adtu_dataset_available
        )
    with adtu_3:
        adtu_epsilon = st.number_input("Epsilon (add dataset to user)", None)
    with adtu_4:
        adtu_delta = st.number_input("Delta (add dataset to user)", None)

    if adtu_username and adtu_dataset and adtu_epsilon and adtu_delta:
        st.write("Click to add dataset", adtu_dataset, "to", adtu_username)
        if st.button(
            "Add dataset to user",
            on_click=add_dataset_to_user,
            args=(
                st.session_state.admin_db,
                adtu_username,
                adtu_dataset,
                adtu_epsilon,
                adtu_delta,
            ),
        ):
            st.write(
                f"Dataset {adtu_dataset} was added to user {adtu_username}."
            )

    st.subheader("Modify user epsilon")
    sue_1, sue_2, sue_3 = st.columns(3)
    with sue_1:
        sue_username = st.selectbox(
            "Username (modify user epsilon)", st.session_state.list_users
        )
    with sue_2:
        if sue_username:
            sue_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.admin_db, sue_username
            )
        else:
            sue_datasets_from_user = st.session_state.list_datasets
        sue_dataset = st.selectbox(
            "Dataset (modify user epsilon)", sue_datasets_from_user
        )
    with sue_3:
        sue_epsilon = st.number_input(
            "Epsilon value (modify user epsilon)", None
        )
    if sue_username and sue_dataset and sue_epsilon:
        st.write(
            "Click to modify initial epsilon value from user",
            sue_username,
            "on dataset",
            sue_dataset,
            "to",
            sue_epsilon,
        )
        if st.button(
            "Modify user epsilon",
            on_click=set_budget_field,
            args=(
                st.session_state.admin_db,
                sue_username,
                sue_dataset,
                "initial_epsilon",
                sue_epsilon,
            ),
        ):
            st.write(f"User {sue_username} epsilon value was modified.")

    st.subheader("Modify user delta")
    sud_1, sud_2, sud_3 = st.columns(3)
    with sud_1:
        sud_username = st.selectbox(
            "Username (modify user delta)", st.session_state.list_users
        )
    with sud_2:
        if sud_username:
            sud_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.admin_db, sud_username
            )
        else:
            sud_datasets_from_user = st.session_state.list_datasets
        sud_dataset = st.selectbox(
            "Dataset (modify user delta)", sud_datasets_from_user
        )
    with sud_3:
        sud_delta = st.number_input("Delta value (modify user delta)", None)
    if sud_username and sud_dataset and sud_delta:
        st.write(
            "Click to modify initial delta value from user",
            sud_username,
            "on dataset",
            sud_dataset,
            "to",
            sud_delta,
        )
        if st.button(
            "Modify user delta",
            on_click=set_budget_field,
            args=(
                st.session_state.admin_db,
                sud_username,
                sud_dataset,
                "initial_delta",
                sud_delta,
            ),
        ):
            st.write(f"User {sud_username} delta value was modified.")

    st.subheader("Modify user may query")
    umq_1, umq_2 = st.columns(2)
    with umq_1:
        umq_username = st.selectbox(
            "Username (user may query)", st.session_state.list_users
        )
    with umq_2:
        umq_may_query = st.selectbox("May query", (True, False))
    if umq_username:
        st.write(
            f"Change user {umq_username} may query to", umq_may_query, "."
        )
        if st.button(
            "Modify user may query",
            on_click=set_may_query,
            args=(st.session_state.admin_db, umq_username, umq_may_query),
        ):
            st.write("User", umq_username, "may_query is now:", umq_may_query)

    st.subheader("Add many users via a yaml file")
    amu_1, amu_2 = st.columns(2)
    with amu_1:
        u_clean = st.toggle(
            "Clean: recreate collection from scratch "
            + "(will delete all previous users)"
        )
    with amu_2:
        u_overwrite = st.toggle(
            "Overwrite: if user already exists, overwrites values"
        )
    u_uploaded_file = st.file_uploader(
        "Choose a YAML file for the user collection",
        accept_multiple_files=False,
    )
    if u_uploaded_file:
        st.write("Click to add users")
        if st.button("Add users"):
            user_collection = yaml.safe_load(u_uploaded_file)
            add_users_via_yaml(
                st.session_state.admin_db,
                user_collection,
                u_clean,
                u_overwrite,
            )
            st.session_state["list_users"] = get_list_of_users(
                st.session_state.admin_db
            )
            st.write("Users were added.")

with dataset_tab:
    st.subheader("Add one dataset")
    ad_1, ad_2, ad_3 = st.columns(3)
    with ad_1:
        ad_dataset = st.text_input("Dataset name (add dataset)", None)
    with ad_2:
        ad_type = st.selectbox(
            "Dataset type (add dataset)",
            (PrivateDatabaseType.PATH, PrivateDatabaseType.S3),
        )
    with ad_3:
        ad_meta_type = st.selectbox(
            "Metadata type (add dataset)",
            (PrivateDatabaseType.PATH, PrivateDatabaseType.S3),
        )
    match ad_type:
        case PrivateDatabaseType.PATH:
            ad_path = st.text_input("Dataset path (add dataset)", None)
        case PrivateDatabaseType.S3:
            ad_s3_1, ad_s3_2, ad_s3_3, ad_s3_4, ad_s3_5 = st.columns(5)
            with ad_s3_1:
                ad_s3_bucket = st.text_input("s3_bucket (add dataset)", None)
            with ad_s3_2:
                ad_s3_key = st.text_input("s3_key (add dataset)", None)
            with ad_s3_3:
                ad_s3_url = st.text_input("endpoint_url (add dataset)", None)
            with ad_s3_4:
                ad_s3_kid = st.text_input(
                    "aws_access_key_id (add dataset)", None
                )
            with ad_s3_5:
                ad_s3_sk = st.text_input("aws_secret_key (add dataset)", None)

    match ad_meta_type:
        case PrivateDatabaseType.PATH:
            ad_meta_path = st.text_input("Metadata path (add dataset)", None)
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
                    "Metadata s3_bucket (add dataset)", None
                )
            with ad_meta_s3_2:
                ad_meta_s3_key = st.text_input(
                    "Metadata s3_key (add dataset)", None
                )
            with ad_meta_s3_3:
                ad_meta_s3_url = st.text_input(
                    "Metadata endpoint_url (add dataset)", None
                )
            with ad_meta_s3_4:
                ad_meta_s3_kid = st.text_input(
                    "Metadata aws_access_key_id (add dataset)", None
                )
            with ad_meta_s3_5:
                ad_meta_s3_sk = st.text_input(
                    "Metadata aws_secret_key (add dataset)", None
                )

    if ad_dataset and ad_type and ad_meta_type:
        keyword_args = {}
        dataset_ready = False
        metadata_ready = False
        button_text = ""
        if ad_type == PrivateDatabaseType.PATH and ad_path:
            keyword_args["dataset_path"] = ad_path
            button_text += f"Add local dataset {ad_dataset} at path {ad_path}"
            dataset_ready = True
        elif (
            ad_type == PrivateDatabaseType.S3
            and ad_s3_bucket
            and ad_s3_key
            and ad_s3_url
            and ad_s3_kid
            and ad_s3_sk
        ):
            keyword_args["s3_bucket"] = ad_s3_bucket
            keyword_args["s3_key"] = ad_s3_key
            keyword_args["endpoint_url"] = ad_s3_url
            keyword_args["aws_access_key_id"] = ad_s3_kid
            keyword_args["aws_secret_access_key"] = ad_s3_sk
            button_text += f"Add S3 dataset {ad_dataset}"
            dataset_ready = True
        else:
            st.write("Please, fill all empty fields for dataset.")

        if ad_meta_type == PrivateDatabaseType.PATH and ad_meta_path:
            keyword_args["metadata_path"] = ad_meta_path
            button_text += f" with local metadata at path {ad_meta_path}"
            metadata_ready = True
        elif (
            ad_meta_type == PrivateDatabaseType.S3
            and ad_meta_s3_bucket
            and ad_meta_s3_key
            and ad_meta_s3_url
            and ad_meta_s3_kid
            and ad_meta_s3_sk
        ):
            keyword_args["metadata_s3_bucket"] = ad_meta_s3_bucket
            keyword_args["metadata_s3_key"] = ad_meta_s3_key
            keyword_args["metadata_endpoint_url"] = ad_meta_s3_url
            keyword_args["metadata_aws_access_key_id"] = ad_meta_s3_kid
            keyword_args["metadata_aws_secret_access_key"] = ad_meta_s3_sk
            button_text += " with S3 metadata"
            metadata_ready = True
        else:
            st.write("Please, fill all empty fields for the metadata.")

        if dataset_ready and metadata_ready:
            if st.button(
                button_text,
                on_click=add_dataset,
                args=(
                    st.session_state.admin_db,
                    ad_dataset,
                    ad_type,
                    ad_meta_type,
                ),
                kwargs=keyword_args,
            ):
                dataset_ready = False
                metadata_ready = False
                st.session_state["list_datasets"] = get_list_of_datasets(
                    st.session_state.admin_db
                )
                st.write("Dataset", ad_dataset, "added.")

    st.subheader("Add many datasets via a yaml file")
    amd_1, amd_2, amd_3 = st.columns(3)
    with amd_1:
        d_clean = st.toggle("Clean: will delete all previous datasets")
    with amd_2:
        d_overwrite_datasets = st.toggle(
            "Overwrite: if dataset already exists, overwrites values"
        )
    with amd_3:
        d_overwrite_metadata = st.toggle(
            "Overwrite: if metadata already exists, overwrites values"
        )
    dataset_collection = st.file_uploader(
        "Select a YAML file for the dataset collection",
        type="yaml",
        accept_multiple_files=False,
    )
    if dataset_collection:
        st.write("Click to add datasets")
        if st.button("Add datasets"):
            dataset_collection = yaml.safe_load(dataset_collection)

            add_datasets_via_yaml(
                st.session_state.admin_db,
                dataset_collection,
                d_clean,
                d_overwrite_datasets,
                d_overwrite_metadata,
            )
            st.session_state["list_datasets"] = get_list_of_datasets(
                st.session_state.admin_db
            )
            st.write("Datasets were added.")

with content_tab:
    st.subheader("Show one element")
    elem_users, elem_archives = st.columns(2)
    with elem_users:
        user_selected = st.selectbox(
            "User to show", st.session_state.list_users
        )
        if st.button(f"Displaying information of: {user_selected}"):
            user_to_show = show_user(st.session_state.admin_db, user_selected)
            st.write(user_to_show)
    with elem_archives:
        user_archives_selected = st.selectbox(
            "Archives from user", st.session_state.list_users
        )
        st.write("Displaying information of:", user_archives_selected)
        if st.button(
            f"Displaying previous queries of: {user_archives_selected}"
        ):
            user_archives_to_show = show_archives_of_user(
                st.session_state.admin_db, user_archives_selected
            )
            st.write(user_archives_to_show)

    elem_datasets, elem_metadata = st.columns(2)
    with elem_datasets:
        dataset_selected = st.selectbox(
            "Dataset to show", st.session_state.list_datasets
        )
        st.write("Displaying information of:", dataset_selected)
        if st.button(f"Displaying dataset: {dataset_selected}"):
            dataset_to_show = show_dataset(
                st.session_state.admin_db, dataset_selected
            )
            st.write(dataset_to_show)
    with elem_metadata:
        metadata_selected = st.selectbox(
            "Metadata to show from dataset", st.session_state.list_datasets
        )
        st.write("Displaying metadata of:", metadata_selected)
        if st.button(f"Displaying metadata of: {metadata_selected}"):
            metadata_to_show = show_metadata_of_dataset(
                st.session_state.admin_db, metadata_selected
            )
            st.write(metadata_to_show)

    st.subheader("Show full collection")
    col_users, col_datasets, col_metadata, col_archives = st.columns(4)
    with col_users:
        if st.button("Show all users"):
            users = show_collection(st.session_state.admin_db, "users")
            st.write(users)
    with col_datasets:
        if st.button("Show all datasets"):
            datasets = show_collection(st.session_state.admin_db, "datasets")
            st.write(datasets)
    with col_metadata:
        if st.button("Show all metadata"):
            metadatas = show_collection(st.session_state.admin_db, "metadata")
            st.write(metadatas)
    with col_archives:
        if st.button(
            "Show archives",
        ):
            archives = show_collection(
                st.session_state.admin_db, "queries_archives"
            )
            st.write(archives)


with deletion_tab:
    _, center, _ = st.columns(3)
    with center:
        st.markdown(
            ":warning: :red[**Danger Zone: deleting is final**] :warning:"
        )

    st.subheader("Delete one element")
    st.markdown("**Delete one user**")
    du_username = st.selectbox(
        "Username (delete user)", st.session_state.list_users
    )
    if du_username:
        st.write(
            "Click to delete user", du_username, "from the list of users."
        )
        if st.button(
            "Delete user",
            on_click=del_user,
            args=(
                st.session_state.admin_db,
                du_username,
            ),
        ):
            st.session_state["list_users"] = get_list_of_users(
                st.session_state.admin_db
            )
            st.write(f"User {du_username} was deleted.")

    st.markdown("**Remove dataset from user**")
    rdtu_1, rdtu_2 = st.columns(2)
    with rdtu_1:
        rdtu_user = st.selectbox(
            "Username (remove dataset from user)", st.session_state.list_users
        )
    with rdtu_2:
        if rdtu_user:
            rdtu_datasets_from_user = get_list_of_datasets_from_user(
                st.session_state.admin_db, rdtu_user
            )
        else:
            rdtu_datasets_from_user = st.session_state.list_datasets
        rdtu_dataset = st.selectbox(
            "Dataset (remove dataset from user)", rdtu_datasets_from_user
        )
    if rdtu_user and rdtu_dataset:
        st.write(
            "Click to remove dataset", rdtu_dataset, "from user", rdtu_user
        )
        if st.button(
            "Remove dataset from user",
            on_click=del_dataset_to_user,
            args=(st.session_state.admin_db, rdtu_user, rdtu_dataset),
        ):
            st.session_state["list_datasets"] = get_list_of_datasets(
                st.session_state.admin_db
            )
            st.write(
                f"Dataset {rdtu_dataset} was removed from user {rdtu_user}."
            )

    st.markdown("**Remove dataset and it's associated metadata**")
    rd_dataset = st.selectbox(
        "Dataset (remove dataset)", st.session_state.list_datasets
    )
    if rd_dataset:
        st.write(
            "Click to delete dataset",
            rd_dataset,
            "from the list of datasets.",
        )
        if st.button(
            "Delete dataset",
            on_click=del_dataset,
            args=(
                st.session_state.admin_db,
                rd_dataset,
            ),
        ):
            st.session_state["list_datasets"] = get_list_of_datasets(
                st.session_state.admin_db
            )
            st.write(f"Dataset {rd_dataset} was deleted.")

    st.subheader("Delete full collection")
    d_col_users, d_col_datasets, d_col_metadata, d_col_archives = st.columns(4)

    with d_col_users:
        if st.button(
            "Delete all users",
            on_click=drop_collection,
            args=(st.session_state.admin_db, "users"),
        ):
            st.session_state["list_users"] = get_list_of_users(
                st.session_state.admin_db
            )
            st.write("Users were all deleted.")

    with d_col_datasets:
        if st.button(
            "Delete all datasets",
            on_click=drop_collection,
            args=(st.session_state.admin_db, "datasets"),
        ):
            st.session_state["list_datasets"] = get_list_of_datasets(
                st.session_state.admin_db
            )
            st.write("Datasets were all deleted.")

    with d_col_metadata:
        if st.button(
            "Delete all metadata",
            on_click=drop_collection,
            args=(st.session_state.admin_db, "metadata"),
        ):
            st.write("Metadata were all deleted.")

    with d_col_archives:
        if st.button(
            "Delete all archives",
            on_click=drop_collection,
            args=(st.session_state.admin_db, "archives"),
        ):
            st.write("Archives were all deleted.")
