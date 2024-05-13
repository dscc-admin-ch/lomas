import docker
import streamlit as st
from administration.mongodb_admin import (
    add_user,
    add_user_with_budget,
    del_user,
    add_dataset_to_user,
    del_dataset_to_user,
    set_budget_field,
    set_may_query,
    show_user,
    create_users_collection,
    add_dataset,
    add_datasets,
    del_dataset,
    drop_collection,
    show_collection,
)
from constants import PrivateDatabaseType


###############################################################################
# BACKEND
###############################################################################


def show_dataset(name):  # TODO in mongodb_admin.py
    print(name)


def show_metadata_of_dataset(name):  # TODO in mongodb_admin.py
    print(name)


def show_archives_of_user(name):  # TODO in mongodb_admin.py
    print(name)


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Admin Database Management")

user_tab, dataset_tab, content_tab, deletion_tab = st.tabs(
    ["User Management", "Dataset Management", "View Database Content", "Delete Content (DANGEROUS)"]
)

if "server_container" not in st.session_state:
    with st.spinner("Loading..."):
        client = docker.DockerClient()
        st.session_state["server_container"] = client.containers.get(
            "lomas_server_dev"
        )

with user_tab:
    st.subheader("Add user")
    au_username = st.text_input("Username (add user)", value="", key=None)
    if au_username:
        st.write("Click to add user", au_username, "to the list of users.")
        if st.button("Add user", on_click=add_user, args=(au_username,)):
            st.write(f"User {au_username} was added.")

    st.subheader("Add user with budget")
    auwb_1, auwb_2, auwb_3, auwb_4 = st.columns(4)
    with auwb_1:
        auwb_username = st.text_input("Username (add user with budget)", None)
    with auwb_2:
        auwb_dataset = st.text_input("Dataset (add user with budget)", None)
    with auwb_3:
        auwb_epsilon = st.number_input("Epsilon (add user with budget)", None)
    with auwb_4:
        auwb_delta = st.number_input("Delta (add user with budget)", None)
    if auwb_username and auwb_dataset and auwb_epsilon and auwb_delta:
        st.write("Click to add user", auwb_username, "to the list of users.")
        if st.button(
            "Add user with dataset",
            on_click=add_user_with_budget,
            args=(auwb_username, auwb_dataset, auwb_epsilon, auwb_delta),
        ):
            st.write(
                f"User {auwb_username} was added with dataset {auwb_dataset}."
            )

    st.subheader("Add dataset to user")
    adtu_1, adtu_2, adtu_3, adtu_4 = st.columns(4)
    with adtu_1:
        adtu_username = st.text_input("Username (add dataset to user)", None)
    with adtu_2:
        adtu_dataset = st.text_input("Dataset (add dataset to user)", None)
    with adtu_3:
        adtu_epsilon = st.number_input("Epsilon (add dataset to user)", None)
    with adtu_4:
        adtu_delta = st.number_input("Delta (add dataset to user)", None)
    if adtu_username and adtu_dataset and adtu_epsilon and adtu_delta:
        st.write("Click to add user", adtu_username, "to the list of users.")
        if st.button(
            "Add user with dataset",
            on_click=add_dataset_to_user,
            args=(adtu_username, adtu_dataset, adtu_epsilon, adtu_delta),
        ):
            st.write(
                f"Dataset {adtu_dataset} was added to user {adtu_username}."
            )

    st.subheader("Modify user epsilon")
    sue_1, sue_2, sue_3 = st.columns(3)
    with sue_1:
        sue_username = st.text_input("Username (modify user epsilon)", None)
    with sue_2:
        sue_dataset = st.text_input("Dataset (modify user epsilon)", None)
    with sue_3:
        sue_epsilon = st.number_input("Epsilon value (modify user epsilon)", None)
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
            "Set user epsilon",
            on_click=set_budget_field,
            args=(sue_username, sue_dataset, "initial_epsilon"),
        ):
            st.write(f"User {sue_username} epsilon value was modified.")

    st.subheader("Modify user delta")
    sud_1, sud_2, sud_3 = st.columns(3)
    with sud_1:
        sud_username = st.text_input("Username (modify user delta)", None)
    with sud_2:
        sud_dataset = st.text_input("Dataset (modify user delta)", None)
    with sud_3:
        sud_delta = st.number_input("Delta value (modify user delta)", None)
    if sue_username and sue_dataset and sud_delta:
        st.write(
            "Click to modify initial delta value from user",
            sud_username,
            "on dataset",
            sud_dataset,
            "to",
            sud_delta,
        )
        if st.button(
            "Modify user epsilon",
            on_click=set_budget_field,
            args=(sud_username, sud_dataset, "initial_delta"),
        ):
            st.write(f"User {sud_username} delta value was modified.")

    st.subheader("Set user may query")
    umq_1, umq_2 = st.columns(2)
    with umq_1:
        umq_username = st.text_input("Username (user may query)", None)
    with umq_2:
        umq_may_query = st.selectbox("May query", (True, False))
    if umq_username and umq_may_query:
        st.write(
            f"Change user {umq_username} may query to", umq_may_query, "."
        )
        if st.button(
            "Set user may query",
            on_click=set_may_query,
            args=(umq_username, umq_may_query),
        ):
            st.write("User", umq_username, "may_query is now:", umq_may_query)

    st.subheader("Add many users via a yaml file")
    amu_1, amu_2 = st.columns(2)
    with amu_1:
        u_clean = st.toggle(
            "Clean: recreate collection from scratch (will delete all previous users)"
        )
    with amu_2:
        u_overwrite = st.toggle(
            "Overwrite: if user already exists, overwrites values"
        )
    u_uploaded_file = st.file_uploader(
        "Choose a YAML file for the user collection",
        accept_multiple_files=False,
    )
    if u_uploaded_file and u_clean and u_overwrite:
        st.write("Click to add users")
        if st.button(
            "Add users",
            on_click=create_users_collection,
            args=(u_clean, u_overwrite, u_uploaded_file),
        ):
            st.write("Users were added.")

with dataset_tab:
    st.subheader("Add one dataset")
    ad_1, ad_2 = st.columns(2)
    with ad_1:
        ad_dataset = st.text_input("Dataset name (add dataset)", None)
    with ad_2:
        ad_type = st.selectbox(
            "Dataset type (add dataset)",
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
                ad_s3_sk = st.text_input(
                    "aws_secret_access_key (add dataset)", None
                )
    uploaded_file = st.file_uploader(
        "Choose a YAML file for dataset metadata",
        accept_multiple_files=False,
    )
    if uploaded_file is not None:
        pass  # TODO modify add dataset such that can give dic directly

    if ad_dataset and ad_type and uploaded_file:
        match ad_type:
            case PrivateDatabaseType.PATH:
                if ad_path:
                    st.write(
                        "Add dataset", ad_dataset, "at path", ad_path, "."
                    )
                    if st.button(
                        "Add dataset",
                        on_click=add_dataset,
                        args=(ad_dataset, ad_type),
                        kwargs=dict(dataset_path=ad_path),
                    ):
                        st.write("Dataset", ad_dataset, "added.")
            case PrivateDatabaseType.S3:
                if (
                    ad_s3_bucket
                    and ad_s3_key
                    and ad_s3_url
                    and ad_s3_kid
                    and ad_s3_sk
                ):
                    st.write("Add dataset", ad_dataset, "on s3.")
                    if st.button(
                        "Add dataset",
                        on_click=add_dataset,
                        args=(ad_dataset, ad_type),
                        kwargs=dict(
                            s3_bucket=ad_s3_bucket,
                            s3_key=ad_s3_key,
                            endpoint_url=ad_s3_url,
                            aws_access_key_id=ad_s3_kid,
                            aws_secret_access_key=ad_s3_sk,
                        ),
                    ):
                        st.write("Dataset", ad_dataset, "added.")

    st.subheader("Add many datasets via a yaml file")
    amd_1, amd_2 = st.columns(2)
    with amd_1:
        d_clean = st.toggle(
            "Clean: recreate collection from scratch (will delete all previous datasets)"
        )
    with amd_2:
        d_overwrite = st.toggle(
            "Overwrite: if dataset already exists, overwrites values"
        )
    uploaded_files = st.file_uploader(
        "Choose a YAML file for the dataset collection and associated metadatas",
        accept_multiple_files=True,
    )
    if uploaded_files and d_clean and d_overwrite:
        st.write("Click to add datasets")
        if st.button(
            "Add datasets",
            on_click=add_datasets,
            args=(d_clean, d_overwrite, uploaded_file),
        ):
            st.write("Datasets were added.")

with content_tab:
    st.subheader("Show full collection")
    col_users, col_datasets, col_metadata, col_archives = st.columns(4)
    with col_users:
        st.button(
            "Show all users",
            on_click=show_collection,
            args=("users"),
        )
        # TODO: display info
    with col_datasets:
        st.button(
            "Show all datasets",
            on_click=show_collection,
            args=("datasets"),
        )
        # TODO: display info
    with col_metadata:
        st.button(
            "Show all metadata",
            on_click=show_collection,
            args=("datasets"),
        )
        # TODO: display info
    with col_archives:
        st.button(
            "Show archives",
            on_click=show_collection,
            args=("archives"),
        )
        # TODO: display info

    st.subheader("Show one element")
    elem_users, elem_archives = st.columns(2)
    list_users = ("Dr. Antartica", "Dr. FSO")  # TODO get from db
    with elem_users:
        user_selected = st.selectbox("User to show", list_users)
        st.button(
            f"Displaying information of: {user_selected}",
            on_click=show_user,
            args=(user_selected),
        )
    with elem_archives:
        option = st.selectbox("Archives from user", list_users)
        st.write("Displaying information of:", option)
        # TODO: display info

    elem_datasets, elem_metadata = st.columns(2)
    list_datasets = ("PENGUIN", "IRIS")  # TODO get from db
    with elem_datasets:
        option = st.selectbox("Dataset to show", list_datasets)
        st.write("Displaying information of:", option)
        # TODO: display info
    with elem_metadata:
        option = st.selectbox("Metadata to show from dataset", list_datasets)
        st.write("Displaying information of:", option)
        # TODO: display info

with deletion_tab:
    st.subheader("Delete full collection")
    d_col_users, d_col_datasets, d_col_metadata, d_col_archives = st.columns(4)
    with d_col_users:
        if st.button(
                "Delete all datasets",
                on_click=drop_collection,
                args=("datasets"),
            ):
                st.write("Datasets were all deleted.")
    
    with d_col_datasets:
        if st.button(
                "Delete all metadata",
                on_click=drop_collection,
                args=("metadata"),
            ):
                st.write("Metadata were all deleted.")

    with d_col_metadata:
        if st.button(
                "Delete all users",
                on_click=drop_collection,
                args=("users"),
            ):
                st.write("Users were all deleted.")
    
    with d_col_archives:
        if st.button(
                "Delete all archives",
                on_click=drop_collection,
                args=("archives"),
            ):
                st.write("Archives were all deleted.")
                
    st.subheader("Delete one element")
    st.markdown("**Delete one user**")
    du_username = st.text_input("Username (delete user)", None)
    if du_username:
        st.write(
            "Click to delete user", du_username, "from the list of users."
        )
        if st.button("Delete user", on_click=del_user, args=(du_username,)):
            st.write(f"User {du_username} was deleted.")

    st.markdown("**Remove dataset from user**")
    rdtu_1, rdtu_2 = st.columns(2)
    with rdtu_1:
        rdtu_username = st.text_input(
            "Username (remove dataset from user)", None
        )
    with rdtu_2:
        rdtu_dataset = st.text_input(
            "Dataset (remove dataset from user)", None
        )
    if rdtu_username and rdtu_dataset:
        st.write(
            "Click to remove dataset", rdtu_dataset, "from user", adtu_username
        )
        if st.button(
            "Remove dataset from user",
            on_click=del_dataset_to_user,
            args=(rdtu_username, rdtu_dataset),
        ):
            st.write(
                f"Dataset {rdtu_dataset} was removed from user {rdtu_username}."
            )

    st.markdown("**Remove dataset**")
    rd_username = st.text_input("Dataset (remove dataset)", None)
    if rd_username:
        st.write(
            "Click to delete dataset",
            rd_username,
            "from the list of datasets.",
        )
        if st.button(
            "Delete dataset", on_click=del_dataset, args=(rd_username,)
        ):
            st.write(f"Dataset {rd_username} was deleted.")