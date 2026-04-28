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

tab1, tab2, tab3, tab4 = st.tabs([
    "Área de estudo",
    "Índices espectrais",
    "Dados de campo",
    "Zonas de manejo"
])

with tab1:
    st.subheader("Área de estudo")

    uploaded_file = st.file_uploader(
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

            st.success("AOI carregada com sucesso.")
    else:
        aoi = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)
        map_center = [-29.67, -53.77]
        st.warning("Usando AOI padrão.")

st.sidebar.header("Configurações")

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

# memória do Streamlit
if "mostrar_mapa" not in st.session_state:
    st.session_state["mostrar_mapa"] = False

if st.sidebar.button("Gerar mapa"):
    st.session_state["mostrar_mapa"] = True

with tab2:
    st.subheader("Índices espectrais")

    if st.session_state["mostrar_mapa"]:
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

            if uploaded_file is not None:
                folium.GeoJson(
                    gdf,
                    name="Limite do talhão"
                ).add_to(m)

            folium.LayerControl().add_to(m)

            st_folium(m, width=1200, height=650)
            
with tab3:
    st.subheader("Dados de campo")

    prod_file = st.file_uploader(
        "Upload mapa de produtividade (.zip shapefile)",
        type=["zip"],
        key="prod"
    )

    if prod_file is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = f"{tmpdir}/prod.zip"

            with open(zip_path, "wb") as f:
                f.write(prod_file.getvalue())

            gdf_prod = gpd.read_file(zip_path)

            if gdf_prod.crs is not None:
                gdf_prod = gdf_prod.to_crs(epsg=4326)

            st.success("Mapa de produtividade carregado")

            col_numericas = gdf_prod.select_dtypes(
                include=["float64", "int64"]
            ).columns

            if len(col_numericas) == 0:
                st.error("Nenhuma coluna numérica encontrada")
            else:
                col_prod = st.selectbox(
                    "Selecione o atributo de produtividade",
                    col_numericas
                )

                gdf_prod[col_prod] = gdf_prod[col_prod].astype(float)
                valores_brutos = gdf_prod[col_prod].dropna()

                st.write("### Estatísticas brutas")
                st.write(valores_brutos.describe())

                usar_filtro = st.checkbox(
                    "Filtrar manualmente valores discrepantes antes da visualização",
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

                    gdf_prod_filtrado = gdf_prod[
                        (gdf_prod[col_prod] >= min_filtro) &
                        (gdf_prod[col_prod] <= max_filtro)
                    ].copy()

                else:
                    gdf_prod_filtrado = gdf_prod.copy()

                st.write(f"Pontos brutos: {len(gdf_prod)}")
                st.write(f"Pontos após filtro: {len(gdf_prod_filtrado)}")

                st.write("### Estatísticas após filtro")
                st.write(gdf_prod_filtrado[col_prod].describe())
                
                from branca.colormap import linear

                st.write("### Mapa de produtividade filtrada")

                vmin = float(gdf_prod_filtrado[col_prod].min())
                vmax = float(gdf_prod_filtrado[col_prod].max())

                colormap = linear.RdYlGn_11.scale(vmin, vmax)
                colormap.caption = f"Produtividade ({col_prod})"

                m2 = folium.Map(
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
                    ).add_to(m2)

                colormap.add_to(m2)

                # Limite do talhão (se existir)
                if uploaded_file is not None:
                    folium.GeoJson(
                        gdf,
                        name="Limite do talhão",
                        style_function=lambda x: {
                            "color": "blue",
                            "weight": 2,
                            "fillOpacity": 0
                        }
                    ).add_to(m2)

                folium.LayerControl().add_to(m2)

                st_folium(m2, height=550)

                m2 = folium.Map(
                    location=map_center,
                    zoom_start=14,
                    tiles="OpenStreetMap"
                )

                folium.GeoJson(
                    gdf_prod_filtrado,
                    name="Produtividade filtrada"
                ).add_to(m2)

                folium.LayerControl().add_to(m2)

                st_folium(m2, height=500)

    else:
        st.info("Faça upload do shapefile de produtividade para iniciar.")