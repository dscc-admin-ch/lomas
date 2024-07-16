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
    The Lomas Administration Dashboard provides a centralized interface for managing various aspects of your server and database.
    Whether you need to monitor server status, manage user accounts, or administer datasets, this dashboard offers a convenient way to do so.
    """  # noqa: E501
    )

    st.header("Key Features")

    st.write(
        """
        - **Server Overview**: Quickly check the status of your server, including live status and configuration details.
        - **Admin Database Management**: Effortlessly manage users and datasets through intuitive interfaces.
        - **User Management**: Add, modify, or delete user accounts, set budget parameters, and control user permissions.
        - **Dataset Management**: Add, remove, or modify datasets and associated metadata with ease.
        - **View Database Content**: Dive deep into the database to view detailed information about users, datasets, metadata, and archives.
        - **Delete Content (DANGEROUS)**: Safely delete users, datasets, metadata, or entire collections when necessary.
        """  # noqa: E501
    )

    st.header("Quick Start")

    st.write(
        """
        1. Navigate through the tabs to access different functionalities:
            - **Server Overview**: Check server status and configuration.
            - **Admin Database Management**: Manage users, datasets, and database content.

        2. Use the intuitive interfaces to perform actions such as adding users, modifying datasets, or viewing database content.

        3. Exercise caution when using deletion functionalities, as they can permanently remove data.

        4. Refer to the documentation or tooltips for additional guidance on specific features.
    """  # noqa: E501
    )

    # Additional resources
    st.header("Resources")

    st.write(
        "**Documentation**: [server documentation](%s)"
        % "https://dscc-admin-ch.github.io/lomas-docs/lomas_server.admin_database.html"  # noqa: E501
    )
    st.write(
        "**Support**: If you encounter any issues or have questions, reach out on [Github issues](%s)"  # noqa: E501
        % "https://github.com/dscc-admin-ch/lomas/issues"
    )
