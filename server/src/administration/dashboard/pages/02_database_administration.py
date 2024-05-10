import streamlit as st
from types import SimpleNamespace

import app
from administration.mongodb_admin import add_user, add_user_with_budget

###############################################################################
# BACKEND
###############################################################################


###############################################################################
# GUI and user interactions
###############################################################################

# Initialization
st.set_page_config(layout="wide")

st.title("Admin database administration")

user_tab, dataset_tab = st.tabs(
    ["User Management", "Dataset Management"]
)

with user_tab:
    st.subheader("Add user")
    username_input = st.text_input("Username", None)
    if username_input:
        st.write("Click to add user", username_input, "to the list of users.")
        add_user_args = SimpleNamespace(user = username_input)
        args = SimpleNamespace(**vars(app.CONFIG.admin_database))
        args.user = username_input
        st.button("Add user", on_click=add_user, args = (add_user_args,))
    

    st.subheader("Add user with budget")