import requests
import streamlit as st


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(fastapi_address, endpoint):
    """Fast api requests on server and cache the result for 60 seconds."""
    response = requests.get(f"{fastapi_address}/{endpoint}", timeout=50)
    if response.status_code == 200:
        return response.json()
    return response.raise_for_status()


def check_user_warning(user: str) -> bool:
    """Verify if user already present and warning if it is.

    Args:
        user (str): name of user

    Returns:
        boolean: True if warning
    """
    if user in st.session_state.list_users:
        st.warning(f"User {user} is already in the database.")
        return True
    return False


def check_dataset_warning(ds: str) -> bool:
    """Verify if dataset already present and warning if it is.

    Args:
        user (str): name of user

    Returns:
        boolean: True if warning
    """
    if ds in st.session_state.list_datasets:
        st.warning(f"Dataset {ds} is already in the database.")
        return True
    return False


def warning_field_missing() -> None:
    """Writes warning that some fields are missing."""
    st.warning("Please fill all fields.")
