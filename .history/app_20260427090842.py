import streamlit as st
import ee
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import tempfile
from modules.maps import add_ee_layer, add_boundary

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
                    
                    st.session_state["gdf_prod_filtrado"] = gdf_prod_filtrado
                    st.session_state["col_prod"] = col_prod

                else:
                    gdf_prod_filtrado = gdf_prod.copy()
                    
                    gdf_prod_filtrado = gdf_prod.copy()
                    st.session_state["gdf_prod_filtrado"] = gdf_prod_filtrado
                    st.session_state["col_prod"] = col_prod

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
                    add_boundary(m, gdf)

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
                
                st.write("### Classes preliminares de produtividade")

                q33 = gdf_prod_filtrado[col_prod].quantile(0.33)
                q66 = gdf_prod_filtrado[col_prod].quantile(0.66)

                def classificar_prod(valor):
                    if valor <= q33:
                        return "Baixa"
                    elif valor <= q66:
                        return "Média"
                    else:
                        return "Alta"

                gdf_prod_filtrado["classe_prod"] = gdf_prod_filtrado[col_prod].apply(classificar_prod)

                st.write(f"Baixa ≤ {q33:.2f}")
                st.write(f"Média: {q33:.2f} a {q66:.2f}")
                st.write(f"Alta > {q66:.2f}")

                st.write(gdf_prod_filtrado["classe_prod"].value_counts())

                m3 = folium.Map(
                    location=map_center,
                    zoom_start=14,
                    tiles="OpenStreetMap"
                )

                cores = {
                    "Baixa": "red",
                    "Média": "yellow",
                    "Alta": "green"
                }

                for classe, cor in cores.items():
                    subset = gdf_prod_filtrado[gdf_prod_filtrado["classe_prod"] == classe]

                    for _, row in subset.iterrows():
                        folium.CircleMarker(
                            location=[row.geometry.y, row.geometry.x],
                            radius=2,
                            color=cor,
                            fill=True,
                            fill_color=cor,
                            fill_opacity=0.7,
                            weight=0,
                            popup=f"{classe} | {col_prod}: {row[col_prod]:.2f}"
                        ).add_to(m3)

                if uploaded_file is not None:
                    add_boundary(m, gdf)

                folium.LayerControl().add_to(m3)

                st_folium(m3, height=550)
                
                st.write("### Interpolação IDW da produtividade filtrada")

                import numpy as np
                from scipy.spatial import cKDTree
                from shapely.geometry import Point
                from shapely.prepared import prep
                import matplotlib.pyplot as plt
                
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

if st.button("Gerar interpolação IDW da produtividade"):

                    if "gdf_prod_filtrado" not in st.session_state:
                        st.warning("Aplique o filtro da produtividade antes de gerar o IDW.")
                    else:
                        gdf_idw = st.session_state["gdf_prod_filtrado"].copy()
                        col_prod = st.session_state["col_prod"]

                        crs_metrico = gdf_idw.estimate_utm_crs()
                        gdf_idw = gdf_idw.to_crs(crs_metrico)

                        x = gdf_idw.geometry.x.values
                        y = gdf_idw.geometry.y.values
                        z = gdf_idw[col_prod].values

                        xmin, ymin, xmax, ymax = gdf_idw.total_bounds

                        grid_x, grid_y = np.mgrid[
                            xmin:xmax:resolucao_idw,
                            ymin:ymax:resolucao_idw
                        ]

                        def idw(x, y, z, xi, yi, power=2, k=8):
                            tree = cKDTree(np.c_[x, y])
                            dist, idx = tree.query(
                                np.c_[xi.flatten(), yi.flatten()],
                                k=k
                            )

                            dist[dist == 0] = 1e-10

                            weights = 1 / dist**power
                            weights /= weights.sum(axis=1, keepdims=True)

                            zi = np.sum(weights * z[idx], axis=1)

                            return zi.reshape(xi.shape)

                        grid_z = idw(
                            x,
                            y,
                            z,
                            grid_x,
                            grid_y,
                            power=power_idw,
                            k=8
                        )

                        st.success("Interpolação gerada com sucesso.")

                        vmin = np.nanmin(grid_z)
                        vmax = np.nanmax(grid_z)

                        st.write(f"Mínimo interpolado: {vmin:.2f}")
                        st.write(f"Máximo interpolado: {vmax:.2f}")

                        fig, ax = plt.subplots(figsize=(8, 6))

                        img = ax.imshow(
                            grid_z.T,
                            extent=(xmin, xmax, ymin, ymax),
                            origin="lower",
                            vmin=vmin,
                            vmax=vmax
                        )

                        gdf_idw.plot(
                            ax=ax,
                            markersize=2,
                            color="black",
                            alpha=0.4
                        )

                        plt.colorbar(img, ax=ax, label=col_prod)

                        ax.set_title("Interpolação IDW da produtividade")
                        ax.set_xlabel("X (m)")
                        ax.set_ylabel("Y (m)")
                        st.pyplot(fig)
                        
                        st.write("### Zonas preliminares sobre a interpolação")

                        q33 = np.nanpercentile(grid_z, 33)
                        q66 = np.nanpercentile(grid_z, 66)

                        zonas_grid = np.where(
                            grid_z <= q33, 1,
                            np.where(grid_z <= q66, 2, 3)
                        )

                        st.write(f"Baixa ≤ {q33:.2f}")
                        st.write(f"Média: {q33:.2f} a {q66:.2f}")
                        st.write(f"Alta > {q66:.2f}")

                        fig2, ax2 = plt.subplots(figsize=(8, 6))

                        img2 = ax2.imshow(
                            zonas_grid.T,
                            extent=(xmin, xmax, ymin, ymax),
                            origin="lower",
                            vmin=1,
                            vmax=3
                        )

                        gdf_idw.plot(
                            ax=ax2,
                            markersize=2,
                            color="black",
                            alpha=0.25
                        )

                        plt.colorbar(
                            img2,
                            ax=ax2,
                            ticks=[1, 2, 3],
                            label="Classe"
                        )

                        ax2.set_title("Zonas preliminares de produtividade")
                        ax2.set_xlabel("X (m)")
                        ax2.set_ylabel("Y (m)")

                        st.pyplot(fig2)