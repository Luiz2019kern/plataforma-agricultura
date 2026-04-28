import ee
import streamlit as st


def init_gee():
    service_account = st.secrets["GEE_SERVICE_ACCOUNT"]
    private_key = st.secrets["GEE_PRIVATE_KEY"]

    private_key = private_key.replace("\\n", "\n")

    credentials = ee.ServiceAccountCredentials(
        service_account,
        key_data={
            "type": "service_account",
            "client_email": service_account,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
    )

    ee.Initialize(
        credentials,
        project="earthengineluizgkern"
    )