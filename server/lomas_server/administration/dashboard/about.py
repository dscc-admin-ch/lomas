import os
import sys
import streamlit as st
from st_pages import Page, show_pages

if __name__ == "__main__":
    # We add the src directory to the python search path
    # Required if the code is not installed as a package via pip/setuptools
    admin_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
    )
    sys.path.append(admin_dir)
    src_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")
    )
    sys.path.append(src_dir)

    st.set_page_config(page_title="Lomas Dashboard")
    FOLDER = "./administration/dashboard"  # TODO move
    show_pages(
        [
            Page(f"{FOLDER}/about.py", "Home Page", "🏠"),
            Page(
                f"{FOLDER}/pages/01_server_overview.py",
                "Lomas server overview",
                ":computer:",
            ),
            Page(
                f"{FOLDER}/pages/02_database_administration.py",
                "Admin database management",
                ":file_folder:",
            ),
        ]
    )

    st.title("Welcome!")

    st.header("Lomas Administation Dashboard")
    st.write(
        """
    The administration dashboard enables to control the state of the server.
    It displays informations about the server and the administration database.
    - In the first tab, informations about the server are shown.
    - In the second tab, it is possible to interact with the administration database to manage:
        - User-related data and
        - Dataset-related data.
    """  # noqa: E501
    )

    st.header("Tabs explanation")

    st.write(
        """
    #### 1. Server overview
    See URL
    See SERVER_STATE (running or not)

    #### 2. Admin database Management
    Enables to manage admin db. # TODO refer to doc or one line each

        - User Management
            - add_user,
            - add_user_with_budget,
            - add_dataset_to_user,
            - set_budget_field,
            - set_may_query,
            - show_user,
            - add_users_via_yaml,

        - Dataset Management (always with metadata)
            - add_dataset,
            - add_datasets_via_yaml,

        - View Database Content
            - full user collection
            - full dataset collection
            - full metadata collection
            - full archives collection
            - a user with all info
            - all queries of a users
            - a dataset will all info
            - metadata of a dataset

        - Delete Content (DANGEROUS)
            - delete full user collection
            - delete full dataset collection
            - delete full metadata collection
            - delete full archives collection
            - delete a user with all info
            - remove dataset from a users
            - delete a dataset
            - delete metadata of a dataset
    """
    )
