import os
from oauthlib.oauth2 import BackendApplicationClient
import requests
from requests_oauthlib import OAuth2Session
import streamlit as st

from lomas_core.models.config import KeycloakClientConfig


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(fastapi_address, endpoint, _kc_config: KeycloakClientConfig):
    """Fast api requests on server and cache the result for 60 seconds."""
    # Disable tls checks if needed
    if not _kc_config.use_tls:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
    # Get JWT token
    oauth_client = BackendApplicationClient(_kc_config.client_id)
    oauth2_session = OAuth2Session(client=oauth_client)
    url_protocol = "https" if _kc_config.use_tls else "http"
    token_url = (
        f"{url_protocol}://{_kc_config.address}:"
        f"{_kc_config.port}/realms/{_kc_config.realm}/protocol/openid-connect/token"
    )
    oauth2_session.fetch_token(
        token_url, client_id=_kc_config.client_id, client_secret=_kc_config.client_secret
    )

    # Perform request
    response = oauth2_session.get(f"{fastapi_address}/{endpoint}", timeout=50)
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
