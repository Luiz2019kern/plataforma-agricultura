import ee
import streamlit as st


def init_gee():
    try:
        service_account = st.secrets["GEE_SERVICE_ACCOUNT"]
        private_key = st.secrets["GEE_PRIVATE_KEY"]

        credentials = ee.ServiceAccountCredentials(
            service_account,
            key_data=private_key
        )

        ee.Initialize(credentials)

    except Exception:
        ee.Initialize(project="earthengineluizgkern")