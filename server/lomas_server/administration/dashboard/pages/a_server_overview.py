# pylint: skip-file
# type: ignore
import streamlit as st

from lomas_core.error_handler import InternalServerException
from lomas_core.models.config import Config as ServerConfig
from lomas_core.models.constants import AdminDBType
from lomas_server.administration.dashboard.config import get_config
from lomas_server.administration.dashboard.utils import get_server_data, get_server_config

###############################################################################
# BACKEND
###############################################################################

try:
    if "dashboard_config" not in st.session_state:
        # Store dashboard config
        st.session_state["dashboard_config"] = get_config()
    if "config" not in st.session_state:
        # Store config
        server_config = get_server_config(st.session_state.dashboard_config)
        st.session_state["config"] = server_config
except InternalServerException as e:
    st.error(f"Failed to load server or dashboard config. Initial exception: {e}")


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas configurations")

if "config" in st.session_state and "dashboard_config" in st.session_state:
    print(st.session_state.dashboard_config)
    st.write(
        "The server is available for requests at the address: "
        + f"https://{st.session_state.dashboard_config.server_url}"
    )

    state_response = get_server_data(st.session_state.dashboard_config, "state")
    if state_response["state"] == "live":
        st.write("The server is live and ready!")
    else:
        st.write("The server is NOT live")

    if st.session_state.config.develop_mode:
        st.write(":red[The server is in DEVELOPMENT mode.]")
    else:
        st.write(":red[The server is in PRODUCTION mode.]")

    tab_1, tab_2 = st.columns(2)
    with tab_1:
        st.subheader("Server configurations")

        st.write(
            "The host IP of the server is:",
            st.session_state.config.server.host_ip,
        )
        st.write(
            "The host port of the server is:",
            st.session_state.config.server.host_port,
        )
        st.write(
            "The method against timing attack is:",
            st.session_state.config.server.time_attack.method,
        )

    with tab_2:
        st.subheader("Administration Database")
        db_type = st.session_state.config.admin_database.db_type
        st.write("The administration database type is:", db_type)
        if db_type == AdminDBType.YAML:
            st.write(
                "The database file is:",
                st.session_state.config.admin_database.db_file,
            )
        elif db_type == AdminDBType.MONGODB:
            st.write(
                "Its address is: ",
                st.session_state.config.admin_database.address,
            )
            st.write("Its port is: ", st.session_state.config.admin_database.port)
            st.write(
                "Its username is: ",
                st.session_state.config.admin_database.username,
            )
            st.write(
                "Its database name is: ",
                st.session_state.config.admin_database.db_name,
            )
        else:
            raise InternalServerException(f"Admin database type {db_type} not supported.")
