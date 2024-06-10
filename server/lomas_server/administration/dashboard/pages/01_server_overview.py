import requests
import streamlit as st

from config import get_config
from constants import AdminDBType, DatasetStoreType
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
        st.session_state["fastapi_url"] = (
            st.session_state.dashboard_config.server_url
        )
        st.session_state["fastapi_address"] = (
            st.session_state.dashboard_config.server_service
        )
except Exception as e:
    st.error(
        f"Failed to load server or dashboard config. Initial exception: {e}"
    )

###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas configurations")

st.write(
    f"The server is available for requests at the address: {st.session_state.fastapi_url}/"
)

response = requests.get(
    f"{st.session_state.fastapi_address}/state", timeout=50
)
if response.status_code == 200:
    response_data = response.json()
    if response_data["state"]["LIVE"]:
        st.write("The server is live and ready!")
    else:
        st.write("The server is NOT live:")
        st.write("Server state:", response_data["state"]["state"])
        st.write("Server messages:", response_data["state"]["message"])
else:
    st.write("Failed to get state. The server is NOT live.")

if st.session_state.config.develop_mode:
    st.write(":red[The server is in DEVELOPMENT mode.]")
else:
    st.write(":red[The server is in PRODUCTION mode.]")


tab_1, tab_2, tab_3 = st.columns(3)
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
            "Its address is: ", st.session_state.config.admin_database.address
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
        raise InternalServerException(
            f"Admin database type {db_type} not supported."
        )

with tab_3:
    st.subheader("Dataset Store")
    ds_store_type = st.session_state.config.dataset_store.ds_store_type
    st.write("The dataset store type is: ", ds_store_type)
    if ds_store_type == DatasetStoreType.LRU:
        st.write(
            "The maximum memory usage is: ",
            st.session_state.config.dataset_store.max_memory_usage,
            "MB.",
        )
        memory_usage_response = requests.get(
            f"{st.session_state.fastapi_address}/get_memory_usage", timeout=50
        )
        if memory_usage_response.status_code == 200:
            memory = memory_usage_response.json()
            st.write(
                "Current memory usage with loaded datasets: ",
                memory["memory_usage"],
                "MB.",
            )
