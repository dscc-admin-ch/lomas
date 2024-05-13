import requests
import streamlit as st


###############################################################################
# BACKEND
###############################################################################
url = "http://lomas_server_dev:80" # TODO get from config

###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas server overview")

st.subheader("Server state")
# state = requests.post(f"{url}/state", timeout=50)
# st.write(f"Server live : {state}")

st.subheader("Server config")
# show config

st.subheader("Server data")
# show memory used ? and other stuff if we want
