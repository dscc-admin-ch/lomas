import streamlit as st

from app import SERVER_STATE

###############################################################################
# BACKEND
###############################################################################


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Lomas server overview")

st.write(f"Server live : {SERVER_STATE['LIVE']}")
