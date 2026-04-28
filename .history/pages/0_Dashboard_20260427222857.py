import streamlit as st

st.title("Dashboard")

st.markdown("## Bem-vindo à plataforma")

col1, col2, col3 = st.columns(3)

col1.metric("Áreas analisadas", 12)
col2.metric("Zonas geradas", 48)
col3.metric("Usuários", 3)

st.markdown("---")

st.write("### Status do sistema")

st.success("Sistema operacional")