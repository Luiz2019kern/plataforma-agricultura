import ee
import streamlit as st


def init_gee():
    key_data = st.secrets["GEE_SERVICE_ACCOUNT_JSON"]

    credentials = ee.ServiceAccountCredentials(
        None,
        key_data=key_data
    )

    ee.Initialize(
        credentials,
        project="earthengineluizgkern"
    )