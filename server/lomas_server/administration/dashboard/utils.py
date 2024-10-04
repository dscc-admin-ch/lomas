import streamlit as st

import requests


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(fastapi_address, endpoint):
    """Fast api requests on server and cache the result for 60 seconds."""
    response = requests.get(f"{fastapi_address}/{endpoint}", timeout=50)
    if response.status_code == 200:
        return response.json()
    return response.raise_for_status()
