import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

from modules.maps import add_ee_layer, add_boundary


st.title("Índices espectrais")

if "aoi" not in st.session_state:
    st.warning("Primeiro carregue o talhão na página Área de estudo.")
    st.stop()

aoi = st.session_state["aoi"]
map_center = st.session_state["map_center"]
gdf = st.session_state.get("gdf_aoi", None)


def preparar_imagem(img):
    return img.divide(10000).copyProperties(img, img.propertyNames())


def add_ndvi(img):
    return img.addBands(
        img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    )


def add_ndre(img):
    return img.addBands(
        img.normalizedDifference(["B8", "B5"]).rename("NDRE")
    )


def add_ndmi(img):
    return img.addBands(
        img.normalizedDifference(["B8", "B11"]).rename("NDMI")
    )


data_inicio = st.date_input("Data início")
data_fim = st.date_input("Data fim")

indice = st.selectbox(
    "Índice espectral",
    ["NDVI", "NDRE", "NDMI"]
)

if st.button("Gerar mapa do índice"):

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(str(data_inicio), str(data_fim))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        .map(preparar_imagem)
    )

    if indice == "NDVI":
        collection = collection.map(add_ndvi)
    elif indice == "NDRE":
        collection = collection.map(add_ndre)
    elif indice == "NDMI":
        collection = collection.map(add_ndmi)

    n_imgs = collection.size().getInfo()
    st.write(f"Imagens encontradas: {n_imgs}")

    if n_imgs == 0:
        st.warning("Nenhuma imagem encontrada para esse período.")
        st.stop()

    img_index = collection.select(indice).mean().clip(aoi)

    st.session_state["img_index"] = img_index
    st.session_state["indice_atual"] = indice

    rgb = (
        collection
        .median()
        .select(["B4", "B3", "B2"])
        .clip(aoi)
    )

    m = folium.Map(
        location=map_center,
        zoom_start=14,
        tiles="OpenStreetMap"
    )

    add_ee_layer(
        m,
        rgb,
        {"min": 0.02, "max": 0.30, "gamma": 1.2},
        "RGB Sentinel-2"
    )

    add_ee_layer(
        m,
        img_index,
        {"min": 0, "max": 1, "palette": ["red", "yellow", "green"]},
        indice
    )

    if gdf is not None:
        add_boundary(m, gdf)

    folium.LayerControl().add_to(m)

    st_folium(m, width=1200, height=650)

    st.success("Índice gerado e salvo para as próximas etapas.")