import streamlit as st
import ee
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import tempfile

PROJECT_ID = "earthengineluizgkern"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate(force=True)
    ee.Initialize(project=PROJECT_ID)

st.title("Plataforma de Agricultura de Precisão")

st.sidebar.header("Configurações")

uploaded_file = st.sidebar.file_uploader(
    "Upload do limite do talhão (.zip shapefile)",
    type=["zip"]
)

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = f"{tmpdir}/area.zip"

        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        gdf = gpd.read_file(zip_path)

        if gdf.crs is not None:
            gdf = gdf.to_crs(epsg=4326)

        geojson = gdf.__geo_interface__
        aoi = ee.FeatureCollection(geojson).geometry()

        centro = gdf.geometry.centroid.iloc[0]
        map_center = [centro.y, centro.x]

        st.sidebar.success("AOI carregada com sucesso.")
else:
    aoi = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)
    map_center = [-29.67, -53.77]
    st.sidebar.warning("Usando AOI padrão.")

data_inicio = st.sidebar.date_input("Data início")
data_fim = st.sidebar.date_input("Data fim")

indice = st.sidebar.selectbox(
    "Índice",
    ["NDVI", "NDRE", "NDMI"]
)

def preparar_imagem(img):
    img = ee.Image(img)
    scaled = img.divide(10000)
    # Envolva o retorno com ee.Image()
    return ee.Image(scaled.copyProperties(img, img.propertyNames()))


def add_ndvi(img):
    img = preparar_imagem(img)
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return img.addBands(ndvi)


def add_ndre(img):
    img = preparar_imagem(img)
    ndre = img.normalizedDifference(["B8", "B6"]).rename("NDRE")
    return img.addBands(ndre)


def add_ndmi(img):
    img = preparar_imagem(img)
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("NDMI")
    return img.addBands(ndmi)

def add_ee_layer(folium_map, ee_image, vis_params, name):
    map_id = ee_image.getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True
    ).add_to(folium_map)

if st.sidebar.button("Gerar mapa"):

    st.write(f"Gerando {indice} de {data_inicio} até {data_fim}")

    collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate(str(data_inicio), str(data_fim))
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
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
    else:
        img_index = collection.select(indice).mean().clip(aoi)

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
            "RGB"
        )

        add_ee_layer(
            m,
            img_index,
            {"min": 0, "max": 1, "palette": ["red", "yellow", "green"]},
            indice
        )

        folium.GeoJson(
            gdf if uploaded_file is not None else None,
            name="Limite do talhão"
        ).add_to(m) if uploaded_file is not None else None

        folium.LayerControl().add_to(m)

        st_folium(m, width=1200, height=650)