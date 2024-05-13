import docker
import streamlit as st
from administration.mongodb_admin import (
    # add_user,
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


###############################################################################
# BACKEND
###############################################################################

def add_user(name):
    print(name)
    pass

###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Admin database management")

user_tab, dataset_tab, content_tab = st.tabs(
    ["User Management", "Dataset Management", "Database Content"]
)

if "server_container" not in st.session_state:
    with st.spinner("Loading..."):
        client = docker.DockerClient()
        st.session_state["server_container"] = client.containers.get(
            "lomas_server_dev"
        )

with user_tab:
    st.subheader("Add user")
    au_username = st.text_input("Username (add user)", value="", key="au_username_input")
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
            st.write(f"User {auwb_username} was added with dataset {auwb_dataset}.")

    st.subheader("Delete user")
    du_username = st.text_input("Username (delete user)", None)
    if du_username:
        st.write(
            "Click to delete user", du_username, "from the list of users."
        )
        if st.button("Delete user", on_click=del_user, args=(du_username,)):
            st.write(f"User {du_username} was deleted.")

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
            st.write(f"Dataset {adtu_dataset} was added to user {adtu_username}.")

    st.subheader("Remove dataset from user")

    st.subheader("Set user epsilon")

    st.subheader("Set user delta")

    st.subheader("Set user may query")

    st.subheader("Show a user")

    st.subheader("Add many users via a yaml file")


with dataset_tab:
    st.subheader("Add one dataset")

    st.subheader("Remove dataset")

    st.subheader("Add many datasets via a yaml file")


with content_tab:
    st.subheader("Show a collection")
    # user, dataset, metadata, (archives ? - do we show archive @Raphael?)

    st.subheader("Show a user")

    st.subheader("Show a dataset")  # TODO function

    st.subheader("Show metadata of a dataset")  # TODO function
