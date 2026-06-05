import httpx
import streamlit as st
from returns.converters import maybe_to_result
from returns.io import IOFailure, IOSuccess
from returns.maybe import Maybe
from returns.pipeline import flow
from returns.pointfree import alt, bind_result, lash, map_
from returns.result import Failure, Success

from lomas_server.administration.dashboard.utils import get_config, query_lomas_auth, recover_if_410


def main() -> None:
    """Main function for the streamlit lomas dashboard."""
    page = st.navigation(
        [
            st.Page(about, title="Home"),
            st.Page(
                "database_administration.py",
                title="Database",
            ),
        ]
    )
    # Sidebar common to all page
    with st.sidebar:
        if not st.user.get("is_logged_in"):
            if st.button("Log in"):
                st.login()
        else:
            st.write(f"**{st.user.name}**")
            if st.button("Log out", type="primary"):
                st.logout()

    page.run()


def about() -> None:
    """About page."""
    st.set_page_config(page_title="Lomas Dashboard")

    st.title("Welcome!")

    st.header("Lomas Administration Dashboard")
    description = """
        The Lomas Administration Dashboard provides a centralized interface for managing various aspects of your server and database.
        Whether you need to monitor server status, manage user accounts, or administer datasets, this dashboard offers a convenient way to do so.
    """
    st.write(description)

    st.header("Key Features")

    features = """
        - **Server Overview**: Quickly check the status of your server, including live status and configuration details.
        - **Admin Database Management**: Effortlessly manage users and datasets through intuitive interfaces.
        - **User Management**: Add, modify, or delete user accounts, set budget parameters, and control user permissions.
        - **Dataset Management**: Add, remove, or modify datasets and associated metadata with ease.
        - **View Database Content**: Dive deep into the database to view detailed information about users, datasets, metadata, and archives.
        - **Delete Content (DANGEROUS)**: Safely delete users, datasets, metadata, or entire collections when necessary.
        """
    st.write(features)

    # Additional resources
    st.header("Resources")

    doc = (
        "**Documentation**: [server documentation]"
        "(https://dscc-admin-ch.github.io/lomas/latest/server/administration/)"
    )
    st.write(doc)
    support = (
        "**Support**: If you encounter any issues or have questions, reach out on [Github issues]"
        "(https://github.com/dscc-admin-ch/lomas/issues)"
    )

    st.write(support)

    # Server Status
    st.header("Server Status")

    match query_lomas_auth("/state", httpx.get):
        case IOSuccess(Success({"state": state})):
            status = f":green-badge[{state}]"
        case IOSuccess(Success(unexpected)):
            status = f":orange-badge[unexpected state: {unexpected}]"
        case IOFailure(Failure(e)):
            status = f":red-badge[unavailable]: {e}"

    match get_config().map(lambda config: config.server_url):
        case IOSuccess(Success(server_url)):
            st.write(f"{status} at {server_url}")
        case IOFailure(Failure(e)):
            st.error(f"Configuration Error: {e}")

    flow(
        get_config(),
        map_(lambda config: Maybe.from_optional(config.dex_config)),
        bind_result(maybe_to_result),
    ).map(
        lambda _: st.write(
            ":red-badge[Dex is enabled.] Dex is only supported for demo purposes and is not safe for a production environment!"
        )
    )

    flow(
        query_lomas_auth("/bootstrap", httpx.get),
        lash(lambda e: recover_if_410(e, default=False)),
        alt(lambda e: st.write(f":red-badge[unavailable]: {e}")),
        map_(lambda e: True if e is None else False),  # Define bootstrap_exists
        map_(
            lambda bootstrap_exists: (
                st.write(
                    ":red-badge[Bootstrap permissions enabled!] Lomas admin api endpoints are authorized with bootstrap credentials. Disable bootstrap permissions!"
                )
                if bootstrap_exists
                else st.write(":green-badge[Bootstrap permissions disabled]")
            )
        ),
    )


if __name__ == "__main__":
    main()
