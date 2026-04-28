import streamlit as st
import ee
import geemap.foliumap as geemap
import geopandas as gpd
import tempfile

PROJECT_ID = "earthengineluizgkern"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate(force=True)
    ee.Initialize(project=PROJECT_ID)

st.title("Plataforma de Agricultura de Precisão")

st.sidebar.header("Configurações")

# =========================
# UPLOAD DA ÁREA
# =========================

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

        aoi = geemap.geopandas_to_ee(gdf).geometry()

        centro = gdf.geometry.centroid.iloc[0]
        map_center = [centro.y, centro.x]

        st.sidebar.success("AOI carregada com sucesso.")
else:
    aoi = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)
    map_center = [-29.67, -53.77]
    st.sidebar.warning("Usando AOI padrão.")

# =========================
# ENTRADAS
# =========================

data_inicio = st.sidebar.date_input("Data início")
data_fim = st.sidebar.date_input("Data fim")

indice = st.sidebar.selectbox(
    "Índice",
    ["NDVI", "NDRE", "NDMI"]
)

# =========================
# FUNÇÕES
# =========================

def add_index(img, indice):
    img = img.divide(10000).copyProperties(img, img.propertyNames())

    if indice == "NDVI":
        index = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    elif indice == "NDRE":
        index = img.normalizedDifference(["B8", "B6"]).rename("NDRE")
    elif indice == "NDMI":
        index = img.normalizedDifference(["B8", "B11"]).rename("NDMI")

    return img.addBands(index)

# =========================
# GERAR MAPA
# =========================

if st.sidebar.button("Gerar mapa"):

    st.write(f"Gerando {indice} de {data_inicio} até {data_fim}")

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(str(data_inicio), str(data_fim))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        .map(lambda img: add_index(img, indice))
    )

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

        Map = geemap.Map(center=map_center, zoom=14)

        Map.addLayer(
            rgb,
            {"min": 0.02, "max": 0.30, "gamma": 1.2},
            "RGB"
        )

        Map.addLayer(
            img_index,
            {"min": 0, "max": 1, "palette": ["red", "yellow", "green"]},
            indice
        )

        Map.addLayer(aoi, {}, "Limite do talhão")

        Map.to_streamlit(height=650)