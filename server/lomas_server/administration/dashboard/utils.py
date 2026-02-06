import os

import streamlit as st
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from lomas_server.models.config import AdminConfig, Config, DexAdminConfig


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(_config: AdminConfig, endpoint: str) -> str:
    """Fast api requests on server and cache the result for 60 seconds."""
    kc_config = _config.kc_config
    assert isinstance(kc_config, DexAdminConfig)
    # Disable tls checks if needed
    if not kc_config.use_tls:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get JWT token
    oauth_client = BackendApplicationClient(kc_config.client_id)
    oauth2_session = OAuth2Session(client=oauth_client)
    oauth2_session.fetch_token(
        kc_config.token_endpoint, client_id=kc_config.client_id, client_secret=kc_config.client_secret
    )

    # Perform request
    response = oauth2_session.get(f"{_config.server_service}/{endpoint}", timeout=50)
    if response.status_code == 200:
        return response.json()
    return response.raise_for_status()


def get_server_config(config: AdminConfig) -> Config:
    """Fetches the server config.

    Args:
        config (Config): The dashboard config.
    """
    return Config.model_validate(get_server_data(config, "config")["config"])
