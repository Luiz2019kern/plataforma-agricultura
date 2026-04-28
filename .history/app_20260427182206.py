import streamlit as st
import ee
import geopandas as gpd
import folium
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from modules.zones import classify_quantiles_grid, classify_quantiles_points


from streamlit_folium import st_folium
from branca.colormap import linear
from scipy.spatial import cKDTree
from modules.interpolation import idw_interpolation

from modules.maps import add_ee_layer, add_boundary
from modules.field_data import (
    read_zip_shapefile,
    get_numeric_columns,
    filter_by_range,
    basic_stats
)

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
        gdf = read_zip_shapefile(uploaded_file)
        geojson = gdf.__geo_interface__
        aoi = ee.FeatureCollection(geojson).geometry()

        centro = gdf.geometry.centroid.iloc[0]
        map_center = [centro.y, centro.x]

        st.success("AOI carregada com sucesso.")
    else:
        gdf = None
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

            if gdf is not None:
                add_boundary(m, gdf)

            folium.LayerControl().add_to(m)
            st_folium(m, width=1200, height=650)
    else:
        st.info("Configure o período, escolha o índice e clique em 'Gerar mapa'.")

with tab3:
    st.subheader("Dados de campo")

    prod_file = st.file_uploader(
        "Upload mapa de produtividade (.zip shapefile)",
        type=["zip"],
        key="prod"
    )

    if prod_file is None:
        st.info("Faça upload do shapefile de produtividade para iniciar.")

    else:
        gdf_prod = read_zip_shapefile(prod_file)
        st.success("Mapa de produtividade carregado.")

        col_numericas = get_numeric_columns(gdf_prod)

        if len(col_numericas) == 0:
            st.error("Nenhuma coluna numérica encontrada.")

        else:
            col_prod = st.selectbox(
                "Selecione o atributo de produtividade",
                col_numericas
            )

            gdf_prod[col_prod] = gdf_prod[col_prod].astype(float)
            valores_brutos = gdf_prod[col_prod].dropna()

            st.write("### Estatísticas brutas")
            st.write(basic_stats(gdf_prod, col_prod))

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

            if gdf is not None:
                add_boundary(m2, gdf)

            folium.LayerControl().add_to(m2)
            st_folium(m2, height=550)

            st.write("### Classes preliminares de produtividade")

            gdf_prod_filtrado, q33, q66 = classify_quantiles_points(
                gdf_prod_filtrado,
                col_prod
                )

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

            if gdf is not None:
                add_boundary(m3, gdf)

            folium.LayerControl().add_to(m3)
            st_folium(m3, height=550)

            st.write("### Interpolação IDW da produtividade filtrada")

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
                st.session_state["grid_z"] = grid_z

                grid_x, grid_y, grid_z, gdf_idw = idw_interpolation(
                    gdf_prod_filtrado,
                    col_prod,
                    resolution=resolucao_idw,
                    power=power_idw
                    )
                xmin, ymin, xmax, ymax = gdf_idw.total_bounds

                st.success("Interpolação gerada com sucesso.")
                
                st.session_state["grid_x"] = grid_
                st.session_state["grid_y"] = grid_y
                st.session_state["grid_z"] = grid_z
                st.session_state["gdf_idw"] = gdf_idw

                vmin_idw = np.nanmin(grid_z)
                vmax_idw = np.nanmax(grid_z)

                st.write(f"Mínimo interpolado: {vmin_idw:.2f}")
                st.write(f"Máximo interpolado: {vmax_idw:.2f}")

                fig, ax = plt.subplots(figsize=(8, 6))

                img = ax.imshow(
                    grid_z.T,
                    extent=(xmin, xmax, ymin, ymax),
                    origin="lower",
                    vmin=vmin_idw,
                    vmax=vmax_idw
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

                zonas_grid, q33_idw, q66_idw = classify_quantiles_grid(grid_z)

                st.write(f"Baixa ≤ {q33_idw:.2f}")
                st.write(f"Média: {q33_idw:.2f} a {q66_idw:.2f}")
                st.write(f"Alta > {q66_idw:.2f}")

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
                
                st.write("### Integração com índice espectral")

            if st.button("Extrair índice nos pontos"):

                if "gdf_prod_filtrado" not in st.session_state:
                    st.warning("Carregue e filtre a produtividade primeiro.")

                elif "img_index" not in st.session_state:
                    st.warning("Gere primeiro o mapa de índice espectral na aba 'Índices espectrais'.")

                else:
                    gdf_pts = st.session_state["gdf_prod_filtrado"].copy()
                    col_prod = st.session_state["col_prod"]
                    imagem = st.session_state["img_index"]
                    indice_usado = st.session_state["indice_atual"]

                    pontos_ee = ee.FeatureCollection(gdf_pts.__geo_interface__)

                    valores = imagem.sampleRegions(
                        collection=pontos_ee,
                        scale=10,
                        geometries=False
                    )

                    df_info = valores.getInfo()
                    lista = [f["properties"] for f in df_info["features"]]
                    
                    df_out = pd.DataFrame(lista)

                    st.write("### Dados combinados")
                    st.dataframe(df_out.head())

                    if indice_usado in df_out.columns:
                        st.write("### Correlação")

                        corr = df_out[[col_prod, indice_usado]].corr().iloc[0, 1]

                        st.write(
                            f"Correlação ({indice_usado} x produtividade): {corr:.3f}"
                        )
                        
                        st.write("### Análise temporal do índice")

if st.button("Analisar melhor data do índice"):

    if "gdf_prod_filtrado" not in st.session_state:
        st.warning("Carregue a produtividade primeiro.")

    else:
        gdf_pts = st.session_state["gdf_prod_filtrado"].copy()
        col_prod = st.session_state["col_prod"]

        pontos_ee = ee.FeatureCollection(gdf_pts.__geo_interface__)

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

        df_res = temporal_correlation(
            collection=collection,
            gdf_points=gdf_pts,
            value_col=col_prod,
            index_name=indice,
            max_images=20,
            scale=10
            )
        
        st.session_state["df_temporal"] = df_res
        st.session_state["df_temporal"] = df_res

        st.write("### Resultado")
        st.dataframe(df_res)

        if "df_temporal" in st.session_state:
            df_res = st.session_state["df_temporal"]

    st.write("### Resultado temporal salvo")
    st.dataframe(df_res)

    if len(df_res) > 0:
        melhor = df_res.loc[df_res["correlacao"].idxmax()]

        st.success(
            f"Melhor data: {melhor['data']} | Correlação: {melhor['correlacao']:.3f}"
        )

        fig, ax = plt.subplots()
        ax.plot(df_res["data"], df_res["correlacao"], marker="o")
        ax.set_title("Correlação ao longo do tempo")
        ax.set_xlabel("Data")
        ax.set_ylabel("Correlação")
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        fig, ax = plt.subplots()
        ax.plot(df_res["data"], df_res["correlacao"], marker="o")
        ax.set_title("Correlação ao longo do tempo")
        ax.set_xlabel("Data")
        ax.set_ylabel("Correlação")
        plt.xticks(rotation=45)
        st.pyplot(fig)

with tab4:
    st.subheader("Zonas de manejo")

    st.write("### Resultados disponíveis")

    if "gdf_prod_filtrado" in st.session_state:
        st.success("Produtividade filtrada disponível")
    else:
        st.warning("Produtividade ainda não carregada/filtrada")

    if "grid_z" in st.session_state:
        st.success("Interpolação IDW disponível")
    else:
        st.warning("Interpolação IDW ainda não gerada")

    if "df_temporal" in st.session_state:
        st.success("Análise temporal disponível")
        st.dataframe(st.session_state["df_temporal"])
    else:
        st.warning("Análise temporal ainda não realizada")
        st.write("### Geração de zona integrada")

if st.button("Gerar zona integrada"):

    if "grid_z" not in st.session_state:
        st.warning("Execute a interpolação primeiro.")

    elif "df_temporal" not in st.session_state:
        st.warning("Execute a análise temporal primeiro.")

    else:
        grid_z = st.session_state["grid_z"]
        df_temp = st.session_state["df_temporal"]

        melhor = df_temp.loc[df_temp["correlacao"].idxmax()]
        melhor_data = melhor["data"]

        st.write(f"Usando melhor data: {melhor_data}")

        # Normalização (0–1)
        prod_norm = (grid_z - np.nanmin(grid_z)) / (
            np.nanmax(grid_z) - np.nanmin(grid_z)
        )

        # Peso simples (pode evoluir depois)
        zona_integrada = prod_norm

        # Classificação final
        zonas_final, q33, q66 = classify_quantiles_grid(zona_integrada)

        st.write("### Zonas integradas")

        fig, ax = plt.subplots(figsize=(8, 6))

        img = ax.imshow(
            zonas_final.T,
            origin="lower",
            vmin=1,
            vmax=3
        )

        plt.colorbar(img, ax=ax, ticks=[1, 2, 3])

        ax.set_title("Zona de manejo integrada")
        st.pyplot(fig)