# import requests
import streamlit as st

from constants import AdminDBType, ConfDatasetStore
from utils.config import get_config
from utils.error_handler import InternalServerException

###############################################################################
# BACKEND
###############################################################################
if "config" not in st.session_state:
    # Store config
    st.session_state["config"] = get_config()

    # Store url
    ip = st.session_state.config.server.host_ip
    port = st.session_state.config.server.host_port
    st.session_state["url"] = f"{ip}:{port}"

###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas configurations")

# TODO after deploy: address from deployment
st.write(
    f"The server is available for requests at the address: {st.session_state.url}"
)

# TODO after deploy: nice to have server LIVE
# state_response = requests.post(f"{st.session_state.url}/state", timeout=50)
# if state_response.state["LIVE"]:
#     st.write("The server is live and ready!")
# else:
#     st.write("The server is not live:")
#     st.write("Server state:", state_response.state["state"])
#     st.write("Server messages:", state_response.state["message"])

st.header("Server configurations")

if st.session_state.config.develop_mode:
    st.write(":red[The server is in DEVELOPMENT mode.]")
else:
    st.write(":red[The server is in PRODUCTION mode.]")

st.write(
    "The host IP of the server is: ", st.session_state.config.server.host_ip
)
st.write(
    "The host port of the server is : ",
    st.session_state.config.server.host_port,
)
st.write(
    "The method against timing attack is: ",
    st.session_state.config.server.time_attack.method,
)

st.subheader("Administration Database")
db_type = st.session_state.config.admin_database.db_type
st.write("The administration database type is: ", db_type)
if db_type == AdminDBType.YAML_TYPE:
    st.write(
        "The database file is: ",
        st.session_state.config.admin_database.db_file,
    )
elif db_type == AdminDBType.MONGODB_TYPE:
    st.write(
        "Its address is: ", st.session_state.config.admin_database.address
    )
    st.write("Its port is: ", st.session_state.config.admin_database.port)
    st.write(
        "Its username is: ", st.session_state.config.admin_database.username
    )
    st.write(
        "Its database name is: ",
        st.session_state.config.admin_database.db_name,
    )
else:
    raise InternalServerException(
        f"Admin database type {db_type} not supported."
    )

st.subheader("Dataset Store")
ds_store_type = st.session_state.config.dataset_store.ds_store_type
st.write("The dataset store type is: ", ds_store_type)
if ds_store_type == ConfDatasetStore.LRU:
    st.write(
        "The maximum memory usage is: ",
        st.session_state.config.dataset_store.max_memory_usage,
    )

    # TODO after deploy: nice to have: get from dataset store
    # memory_usage = requests.post(
    #     f"{st.session_state.url}/get_memory_usage", timeout=50
    # )
    # st.write(
    #     "Current memory usage with loaded datasets: ",
    #     memory_usage,
    # )
