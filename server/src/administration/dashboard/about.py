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

    st.header("Introduction")
    st.write("""
    Lomas dashboard
    """)

    st.header("Tabs explanation")

    st.write("""
    #### 1. Server overview
    See URL
    See SERVER_STATE (running or not)

    #### 2. Admin database Management
    Enables to manage admin db. 
        user (add, remove, may_query) etc
        datasets (add, remove, metadata) etc
    """)
