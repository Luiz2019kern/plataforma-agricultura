import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

from modules.field_data import read_zip_shapefile
from modules.maps import add_boundary
from utils.gee import init_gee

init_gee()


st.title("Área de estudo")

uploaded_file = st.file_uploader(
    "Upload do limite do talhão (.zip shapefile)",
    type=["zip"]
)

if uploaded_file is not None:
    gdf = read_zip_shapefile(uploaded_file)

    geojson = gdf.__geo_interface__
    aoi = ee.FeatureCollection(geojson).geometry()

    centro = gdf.geometry.centroid.iloc[0]
    map_center = [centro.y, centro.x]

    st.session_state["gdf_aoi"] = gdf
    st.session_state["aoi"] = aoi
    st.session_state["map_center"] = map_center

    st.success("Área de estudo carregada com sucesso.")

    m = folium.Map(
        location=map_center,
        zoom_start=15,
        tiles="OpenStreetMap"
    )

    add_boundary(m, gdf)

    st_folium(m, width=1200, height=600)

else:
    st.warning("Carregue o shapefile do talhão para iniciar.")