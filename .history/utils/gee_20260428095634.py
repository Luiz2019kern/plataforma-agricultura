import ee
import streamlit as st


def init_gee():
    if st.session_state.get("gee_initialized", False):
        return

    service_account = st.secrets["GEE_SERVICE_ACCOUNT"]
    private_key = st.secrets["GEE_PRIVATE_KEY"]

    credentials = ee.ServiceAccountCredentials(
        service_account,
        key_data={
            "client_email": service_account,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
    )

    ee.Initialize(credentials)

    st.session_state["gee_initialized"] = True