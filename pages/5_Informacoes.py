import streamlit as st
from utils.weather import get_weather


st.title("Informações do município")

cidade = st.text_input("Digite o município")

if st.button("Buscar informações"):

    dados = get_weather(cidade)

    if dados is None:
        st.error("Não foi possível obter dados.")
        st.stop()

    st.success(f"Dados para {dados['cidade']}")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    col1.metric("Temperatura", f"{dados['temp']} °C")
    col2.metric("Umidade", f"{dados['umidade']}%")
    col3.metric("Vento", f"{dados['vento']} m/s")

    st.write(f"Clima: {dados['descricao']}")

    st.markdown("---")

    st.write("### Localização")

    st.write(f"Latitude: {dados['lat']}")
    st.write(f"Longitude: {dados['lon']}")