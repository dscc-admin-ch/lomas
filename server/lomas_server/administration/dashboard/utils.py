import os

import streamlit as st
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from lomas_core.models.config import Config as ServerConfig
from lomas_server.administration.dashboard.config import Config


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(_config: Config, endpoint):
    """Fast api requests on server and cache the result for 60 seconds."""
    # Disable tls checks if needed
    if not _config.kc_config.use_tls:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get JWT token
    oauth_client = BackendApplicationClient(_config.kc_config.client_id)
    oauth2_session = OAuth2Session(client=oauth_client)
    url_protocol = "https" if _config.kc_config.use_tls else "http"
    token_url = (
        f"{url_protocol}://{_config.kc_config.address}:"
        f"{_config.kc_config.port}/realms/{_config.kc_config.realm}/protocol/openid-connect/token"
    )
    oauth2_session.fetch_token(
        token_url, client_id=_config.kc_config.client_id, client_secret=_config.kc_config.client_secret
    )

    # Perform request
    response = oauth2_session.get(f"{_config.server_service}/{endpoint}", timeout=50)
    if response.status_code == 200:
        return response.json()
    return response.raise_for_status()


def get_server_config(config: Config):
    """Fetches the server config.

    Args:
        config (Config): The dashboard config.
    """
    return ServerConfig.model_validate(get_server_data(config, "config")["config"])


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
