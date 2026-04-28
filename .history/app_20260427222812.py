import streamlit as st
import ee
from utils.auth import login

PROJECT_ID = "earthengineluizgkern"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate(force=True)
    ee.Initialize(project=PROJECT_ID)


st.set_page_config(
    page_title="Plataforma de Agricultura de Precisão",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔐 Controle de login
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    login()
    st.stop()


# 🟢 PLATAFORMA LIBERADA
st.title("Plataforma de Agricultura de Precisão")

st.markdown("""
### Sistema de suporte à decisão

Bem-vindo à plataforma.

Use o menu lateral para navegar.
""")