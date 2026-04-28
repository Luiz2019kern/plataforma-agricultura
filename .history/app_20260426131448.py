import streamlit as st
import ee
import geemap

# inicializar GEE
try:
    ee.Initialize()
except:
    ee.Authenticate()
    ee.Initialize()

st.title("Plataforma de Agricultura de Precisão")

st.sidebar.header("Configurações")

# entrada de datas
data_inicio = st.sidebar.date_input("Data início")
data_fim = st.sidebar.date_input("Data fim")

indice = st.sidebar.selectbox(
    "Índice",
    ["NDVI", "NDRE", "NDMI"]
)

if st.sidebar.button("Gerar mapa"):

    st.write(f"Gerando {indice} de {data_inicio} até {data_fim}")

    aoi = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)

    collection = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(str(data_inicio), str(data_fim))
        .map(lambda img: img.divide(10000))
    )

    if indice == "NDVI":
        def calc(img):
            return img.addBands(img.normalizedDifference(['B8','B4']).rename('NDVI'))
    elif indice == "NDRE":
        def calc(img):
            return img.addBands(img.normalizedDifference(['B8','B6']).rename('NDRE'))
    else:
        def calc(img):
            return img.addBands(img.normalizedDifference(['B8','B11']).rename('NDMI'))

    collection = collection.map(calc)

    img = collection.select(indice).mean().clip(aoi)

    Map = geemap.Map(center=[-29.67, -53.77], zoom=12)

    Map.addLayer(
        img,
        {'min':0, 'max':1, 'palette':['red','yellow','green']},
        indice
    )

    Map.to_streamlit(height=600)