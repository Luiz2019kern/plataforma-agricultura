import ee
import streamlit as st


def init_gee():
    if st.session_state.get("gee_initialized"):
        return

    ee.Initialize(project="earthengineluizgkern")

    st.session_state["gee_initialized"] = True