import streamlit as st
import folium
import numpy as np
import matplotlib.pyplot as plt

from streamlit_folium import st_folium
from branca.colormap import linear

from modules.field_data import (
    read_zip_shapefile,
    get_numeric_columns,
    filter_by_range,
    basic_stats
)

from modules.maps import add_boundary
from modules.interpolation import idw_interpolation
from modules.zones import classify_quantiles_points, classify_quantiles_grid


st.title("Produtividade e interpolação")

if "aoi" not in st.session_state:
    st.warning("Primeiro carregue o talhão na página Área de estudo.")
    st.stop()

map_center = st.session_state["map_center"]
gdf_aoi = st.session_state.get("gdf_aoi", None)

prod_file = st.file_uploader(
    "Upload do mapa de produtividade (.zip shapefile)",
    type=["zip"]
)

if prod_file is None:
    st.info("Carregue o shapefile de produtividade para iniciar.")
    st.stop()

gdf_prod = read_zip_shapefile(prod_file)
st.success("Mapa de produtividade carregado.")

col_numericas = get_numeric_columns(gdf_prod)

if len(col_numericas) == 0:
    st.error("Nenhuma coluna numérica encontrada no shapefile.")
    st.stop()

col_prod = st.selectbox(
    "Selecione o atributo de produtividade",
    col_numericas
)

gdf_prod[col_prod] = gdf_prod[col_prod].astype(float)
valores_brutos = gdf_prod[col_prod].dropna()

st.write("### Estatísticas brutas")
st.write(basic_stats(gdf_prod, col_prod))

usar_filtro = st.checkbox(
    "Filtrar manualmente valores discrepantes",
    value=True
)

if usar_filtro:
    min_filtro = st.number_input(
        "Valor mínimo aceito",
        value=float(valores_brutos.min())
    )

    max_filtro = st.number_input(
        "Valor máximo aceito",
        value=float(valores_brutos.max())
    )

    gdf_prod_filtrado = filter_by_range(
        gdf_prod,
        col_prod,
        min_filtro,
        max_filtro
    )
else:
    gdf_prod_filtrado = gdf_prod.copy()

st.session_state["gdf_prod_filtrado"] = gdf_prod_filtrado
st.session_state["col_prod"] = col_prod

st.write(f"Pontos brutos: {len(gdf_prod)}")
st.write(f"Pontos após filtro: {len(gdf_prod_filtrado)}")

st.write("### Estatísticas após filtro")
st.write(basic_stats(gdf_prod_filtrado, col_prod))

st.write("### Mapa de produtividade filtrada")

vmin = float(gdf_prod_filtrado[col_prod].min())
vmax = float(gdf_prod_filtrado[col_prod].max())

colormap = linear.RdYlGn_11.scale(vmin, vmax)
colormap.caption = f"Produtividade ({col_prod})"

m = folium.Map(
    location=map_center,
    zoom_start=14,
    tiles="OpenStreetMap"
)

for _, row in gdf_prod_filtrado.iterrows():
    valor = row[col_prod]

    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=2,
        color=colormap(valor),
        fill=True,
        fill_color=colormap(valor),
        fill_opacity=0.7,
        weight=0,
        popup=f"{col_prod}: {valor:.2f}"
    ).add_to(m)

colormap.add_to(m)

if gdf_aoi is not None:
    add_boundary(m, gdf_aoi)

st_folium(m, width=1200, height=550)

st.write("### Classes preliminares de produtividade")

gdf_classes, q33, q66 = classify_quantiles_points(
    gdf_prod_filtrado,
    col_prod
)

st.write(f"Baixa ≤ {q33:.2f}")
st.write(f"Média: {q33:.2f} a {q66:.2f}")
st.write(f"Alta > {q66:.2f}")

st.write(gdf_classes["classe_prod"].value_counts())

st.write("### Interpolação IDW")

resolucao_idw = st.slider(
    "Resolução da interpolação IDW (m)",
    min_value=5,
    max_value=30,
    value=10,
    step=5
)

power_idw = st.slider(
    "Potência do IDW",
    min_value=1,
    max_value=4,
    value=2,
    step=1
)

if st.button("Gerar IDW da produtividade"):

    grid_x, grid_y, grid_z, gdf_idw = idw_interpolation(
        gdf_prod_filtrado,
        col_prod,
        resolution=resolucao_idw,
        power=power_idw
    )

    xmin, ymin, xmax, ymax = gdf_idw.total_bounds

    st.session_state["grid_x"] = grid_x
    st.session_state["grid_y"] = grid_y
    st.session_state["grid_z"] = grid_z
    st.session_state["gdf_idw"] = gdf_idw
    st.session_state["resolucao_idw"] = resolucao_idw
    st.session_state["power_idw"] = power_idw

    st.success("IDW da produtividade gerado com sucesso.")

    fig, ax = plt.subplots(figsize=(8, 6))

    img = ax.imshow(
        grid_z.T,
        extent=(xmin, xmax, ymin, ymax),
        origin="lower"
    )

    gdf_idw.plot(
        ax=ax,
        markersize=2,
        color="black",
        alpha=0.25
    )

    plt.colorbar(img, ax=ax, label=col_prod)

    ax.set_title("Interpolação IDW da produtividade")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    st.pyplot(fig)

    st.write("### Zonas preliminares da produtividade")

    zonas_grid, q33_idw, q66_idw = classify_quantiles_grid(grid_z)

    st.write(f"Baixa ≤ {q33_idw:.2f}")
    st.write(f"Média: {q33_idw:.2f} a {q66_idw:.2f}")
    st.write(f"Alta > {q66_idw:.2f}")

    st.session_state["zonas_prod"] = zonas_grid