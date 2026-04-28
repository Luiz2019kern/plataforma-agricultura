import json
import ee
import streamlit as st


def init_gee():
    service_account = st.secrets["GEE_SERVICE_ACCOUNT"]
    private_key = st.secrets["GEE_PRIVATE_KEY"]

    private_key = private_key.replace("\\n", "\n")

    key_data = {
        "type": "service_account",
        "client_email": service_account,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials = ee.ServiceAccountCredentials(
        service_account,
        key_data=json.dumps(key_data)
    )

    ee.Initialize(
        credentials,
        project="earthengineluizgkern"
    )