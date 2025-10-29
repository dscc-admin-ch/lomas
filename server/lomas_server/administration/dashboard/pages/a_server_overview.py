import streamlit as st

from lomas_core.error_handler import InternalServerException
from lomas_server.administration.dashboard.utils import get_server_config, get_server_data
from lomas_server.models.config import AdminConfig

# Initialization
st.title("Lomas configurations")

###############################################################################
# BACKEND
###############################################################################

try:
    if "dashboard_config" not in st.session_state:
        # Store dashboard config
        st.session_state["dashboard_config"] = AdminConfig()
    if "config" not in st.session_state:
        # Store config
        server_config = get_server_config(st.session_state.dashboard_config)
        st.session_state["config"] = server_config
except InternalServerException as e:
    st.error(f"Failed to load server or dashboard config. Initial exception: {e}")


###############################################################################
# GUI and user interactions
###############################################################################

if "config" in st.session_state and "dashboard_config" in st.session_state:
    st.write(
        f"The server is available for requests at the address: {st.session_state.dashboard_config.server_url}"
    )

    state_response = get_server_data(st.session_state.dashboard_config, "state")
    if state_response["state"] == "live":
        st.write("The server is live and ready!")
    else:
        st.write("The server is NOT live")

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
        st.write(
            "Its address is: ",
            st.session_state.config.admin_database_url,
        )
