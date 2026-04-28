import streamlit as st
import ee
from utils.auth import login

st.info("Siga o fluxo recomendado para garantir consistência dos dados.")


st.sidebar.image("assets/logo.png", use_container_width=True)

st.sidebar.markdown("## Plataforma AP")
st.sidebar.markdown("---")

st.sidebar.success("Sistema ativo")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
st.title("Nome da página")
st.markdown("---")

st.markdown("""
### Sistema de suporte à decisão

Bem-vindo à plataforma.

Use o menu lateral para navegar.
""")