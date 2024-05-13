import os
import sys
import streamlit as st
from st_pages import Page, show_pages

if __name__ == "__main__":
    # We add the src directory to the python search path
    # This is required if the code is not installed as a package via pip/setuptools
    admin_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
    )
    sys.path.append(admin_dir)
    src_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")
    )
    sys.path.append(src_dir)
    
    st.set_page_config(page_title="Lomas Dashboard")
    show_pages(
        [
            Page("./administration/dashboard/about.py", "Home Page", "🏠"),
            Page(
                "./administration/dashboard/pages/01_server_overview.py",
                "Lomas server overview",
                ":computer:",
            ),
            Page(
                "./administration/dashboard/pages/02_database_administration.py",
                "Admin database management",
                ":file_folder:",
            ),
        ]
    )
    
    st.title("Welcome!")

    st.header("Lomas Administation Dashboard")
    st.write("""
    Users, datasets metadata and archives are managed via an 'admninistration database'. 
    Currently, the database is a MongoDB database is used. 
    - User-related data include access permissions to specific datasets, allocated budgets for each user, remaining budgets and queries executed so far by the user (that we also refer to as "archives"). 
    - Dataset-related data includes details such as dataset names, information and credentials for accessing the sensitive dataset (e.g., S3, local, HTTP), and references to associated metadata.
    """)

    st.header("Tabs explanation")

    st.write("""
    #### 1. Server overview
    See URL
    See SERVER_STATE (running or not)

    #### 2. Admin database Management
    Enables to manage admin db. 
    
        - User Management
            - add_user,
            - add_user_with_budget,
            - del_user,
            - add_dataset_to_user,
            - del_dataset_to_user,
            - set_budget_field,
            - set_may_query,
            - show_user,
            - create_users_collection,

        - Dataset Management (always with metadata)
            - add_dataset,
            - add_datasets,
            - del_dataset,

        - Database Content (quick global overview)
            - full user collection 
            - full dataset collection 
            - full metadata collection
            - full archives collection
            - a user with all info + all his/her queries.
            - a dataset will all info + metadata + all queries and by who on it (use archive as well).
    """)
