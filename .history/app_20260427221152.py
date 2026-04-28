import streamlit as st
import ee

PROJECT_ID = "earthengineluizgkern"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate(force=True)
    ee.Initialize(project=PROJECT_ID)


st.set_page_config(
    page_title="Plataforma de Agricultura de Precisão",
    layout="wide"
)

st.title("Plataforma de Agricultura de Precisão")

st.markdown("""
### Sistema de suporte à decisão para geração de zonas de manejo

Esta plataforma integra:

- Sensoriamento remoto com Google Earth Engine
- Dados de produtividade
- Interpolação espacial
- Índices espectrais
- Zonas de manejo multivariadas

Use o menu lateral para navegar entre as etapas do processamento.
""")

st.info("Fluxo recomendado: Área de estudo → Índices espectrais → Produtividade → Zonas de manejo")