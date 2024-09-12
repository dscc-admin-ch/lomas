import requests
import streamlit as st
from config import get_config

from constants import AdminDBType
from utils.config import get_config as get_server_config
from utils.error_handler import InternalServerException

###############################################################################
# BACKEND
###############################################################################

try:
    if "config" not in st.session_state:
        # Store config
        st.session_state["config"] = get_server_config()
    if "dashboard_config" not in st.session_state:
        # Store dashboard config
        st.session_state["dashboard_config"] = get_config()
except Exception as e:
    st.error(
        f"Failed to load server or dashboard config. Initial exception: {e}"
    )


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_server_data(fastapi_address, endpoint):
    """Fast api requests on server and cache the result for 60 seconds"""
    response = requests.get(f"{fastapi_address}/{endpoint}", timeout=50)
    if response.status_code == 200:
        return response.json()
    return response.raise_for_status()


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas configurations")

if "config" in st.session_state and "dashboard_config" in st.session_state:
    st.write(
        "The server is available for requests at the address: "
        + f"https://{st.session_state.dashboard_config.server_url}"
    )

    state_response = get_server_data(
        st.session_state.dashboard_config.server_service, "state"
    )
    if state_response["state"]["LIVE"]:
        st.write("The server is live and ready!")
    else:
        st.write("The server is NOT live:")
        st.write("Server state:", state_response["state"]["state"])
        st.write("Server messages:", state_response["state"]["message"])

    if st.session_state.config.develop_mode:
        st.write(":red[The server is in DEVELOPMENT mode.]")
    else:
        st.write(":red[The server is in PRODUCTION mode.]")

    tab_1, tab_2 = st.columns(2)
    with tab_1:
        st.subheader("Server configurations")

        st.write(
            "The host IP of the server is: ",
            st.session_state.config.server.host_ip,
        )
        st.write(
            "The host port of the server is : ",
            st.session_state.config.server.host_port,
        )
        st.write(
            "The method against timing attack is: ",
            st.session_state.config.server.time_attack.method,
        )

    with tab_2:
        st.subheader("Administration Database")
        db_type = st.session_state.config.admin_database.db_type
        st.write("The administration database type is: ", db_type)
        if db_type == AdminDBType.YAML:
            st.write(
                "The database file is: ",
                st.session_state.config.admin_database.db_file,
            )
        elif db_type == AdminDBType.MONGODB:
            st.write(
                "Its address is: ",
                st.session_state.config.admin_database.address,
            )
            st.write(
                "Its port is: ", st.session_state.config.admin_database.port
            )
            st.write(
                "Its username is: ",
                st.session_state.config.admin_database.username,
            )
            st.write(
                "Its database name is: ",
                st.session_state.config.admin_database.db_name,
            )
        else:
            raise InternalServerException(
                f"Admin database type {db_type} not supported."
            )
