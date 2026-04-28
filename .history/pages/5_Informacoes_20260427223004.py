import streamlit as st

st.title("Informações do município")

municipio = st.text_input("Município")

if municipio:
    st.write(f"Informações para: {municipio}")

    # MOCK (depois conectamos API real)
    st.write("Estado: RS")
    st.write("Altitude média: 120 m")
    st.write("Clima: Subtropical")