import streamlit as st

st.title("Dashboard")

st.markdown("### Visão geral do sistema")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Áreas analisadas", "12")

with col2:
    st.metric("Zonas geradas", "48")

with col3:
    st.metric("Processamentos", "126")

st.markdown("---")

st.markdown("### Status")

col1, col2 = st.columns(2)

with col1:
    st.success("✔ Sistema operacional")
    st.success("✔ GEE conectado")

with col2:
    st.info("ℹ️ Última análise: hoje")
    st.info("ℹ️ Usuário ativo")

st.markdown("---")

st.markdown("### Navegação recomendada")

st.write("""
1. Definir área de estudo  
2. Gerar índices espectrais  
3. Inserir produtividade  
4. Gerar zonas de manejo  
""")