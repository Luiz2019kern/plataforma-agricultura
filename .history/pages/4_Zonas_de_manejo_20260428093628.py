import ee
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from modules.zones import (
    weighted_overlay,
    classify_management_zones
)
from modules.interpolation import idw_interpolation
from utils.gee import init_gee

init_gee()


st.title("Zonas de manejo multivariadas")

# 🔴 Validações
if "grid_z" not in st.session_state:
    st.warning("👉 Primeiro gere a interpolação da produtividade.")
    st.stop()

if "img_index" not in st.session_state:
    st.warning("👉 Primeiro gere o índice espectral.")
    st.stop()

if "gdf_prod_filtrado" not in st.session_state:
    st.warning("👉 Primeiro carregue e filtre a produtividade.")
    st.stop()


grid_z = st.session_state["grid_z"]
img_index = st.session_state["img_index"]
gdf_prod = st.session_state["gdf_prod_filtrado"]
indice_nome = st.session_state["indice_atual"]

resolucao = st.session_state.get("resolucao_idw", 10)
power = st.session_state.get("power_idw", 2)

# 🔥 EXTRAIR ÍNDICE NOS PONTOS
st.write("### Integração produtividade + índice")

if st.button("Extrair índice e gerar grid do índice"):

    gdf_pts = gdf_prod.copy()

    if len(gdf_pts) > 5000:
        gdf_pts = gdf_pts.sample(n=5000, random_state=42)
        st.warning("Amostrando 5000 pontos para evitar limite do Earth Engine.")

    pontos_ee = ee.FeatureCollection(gdf_pts.__geo_interface__)

    valores = img_index.sampleRegions(
        collection=pontos_ee,
        scale=10,
        geometries=False
    )

    df_info = valores.limit(5000).getInfo()
    lista = [f["properties"] for f in df_info["features"]]

    import pandas as pd
    df = pd.DataFrame(lista)

    if indice_nome not in df.columns:
        st.error("Erro ao extrair índice.")
        st.stop()

    gdf_pts[indice_nome] = df[indice_nome]

    st.success("Índice extraído com sucesso.")

    # 🔥 INTERPOLAÇÃO DO ÍNDICE
    grid_x_i, grid_y_i, grid_indice, _ = idw_interpolation(
        gdf_pts,
        indice_nome,
        resolution=resolucao,
        power=power
    )

    st.session_state["grid_indice"] = grid_indice

    st.success("Grid do índice gerado.")

# 🔴 Verificação
if "grid_indice" not in st.session_state:
    st.info("👉 Clique no botão acima para gerar o grid do índice.")
    st.stop()

grid_indice = st.session_state["grid_indice"]

# 🔴 Checagem crítica
if grid_indice.shape != grid_z.shape:
    st.error("Grid do índice e da produtividade não possuem o mesmo tamanho.")
    st.stop()

# 🎯 PESOS
st.write("### Definição de pesos")

peso_prod = st.slider("Peso da produtividade", 0.0, 1.0, 0.6, 0.1)
peso_indice = st.slider("Peso do índice", 0.0, 1.0, 0.4, 0.1)

soma = peso_prod + peso_indice

if soma == 0:
    st.warning("A soma dos pesos não pode ser zero.")
    st.stop()

peso_prod /= soma
peso_indice /= soma

# 🔥 ZONA MULTIVARIADA
arrays = {
    "produtividade": grid_z,
    "indice": grid_indice
}

weights = {
    "produtividade": peso_prod,
    "indice": peso_indice
}

score = weighted_overlay(arrays, weights)
zonas = classify_management_zones(score, n_classes=3)

st.session_state["zonas_final"] = zonas

# 📊 VISUALIZAÇÃO
st.write("### Resultado")

fig, ax = plt.subplots(figsize=(8, 6))

img = ax.imshow(
    zonas.T,
    origin="lower",
    vmin=1,
    vmax=3
)

plt.colorbar(img, ax=ax, ticks=[1, 2, 3], label="Classe")

ax.set_title("Zonas de manejo multivariadas")

st.pyplot(fig)

st.success("Zonas de manejo geradas com sucesso.")