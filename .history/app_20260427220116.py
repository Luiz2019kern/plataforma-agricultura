import streamlit as st
import ee
import geopandas as gpd
import folium
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from streamlit_folium import st_folium
from branca.colormap import linear

from modules.maps import add_ee_layer, add_boundary
from modules.field_data import (
    read_zip_shapefile,
    get_numeric_columns,
    filter_by_range,
    basic_stats,
)
from modules.interpolation import idw_interpolation
from modules.zones import (
    classify_quantiles_grid,
    classify_quantiles_points,
    weighted_overlay,
    classify_management_zones,
)
from modules.analysis import temporal_correlation


# =========================================================
# CONFIGURAÇÃO GERAL
# =========================================================

PROJECT_ID = "earthengineluizgkern"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate(force=True)
    ee.Initialize(project=PROJECT_ID)

st.set_page_config(page_title="Plataforma de Agricultura de Precisão", layout="wide")
st.title("Plataforma de Agricultura de Precisão")


# =========================================================
# FUNÇÕES GEE
# =========================================================

def preparar_imagem(img):
    """Aplica fator de escala às bandas Sentinel-2 SR."""
    return img.divide(10000).copyProperties(img, img.propertyNames())


def add_ndvi(img):
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return img.addBands(ndvi)


def add_ndre(img):
    ndre = img.normalizedDifference(["B8", "B5"]).rename("NDRE")
    return img.addBands(ndre)


def add_ndmi(img):
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("NDMI")
    return img.addBands(ndmi)


INDEX_FUNCTIONS = {
    "NDVI": add_ndvi,
    "NDRE": add_ndre,
    "NDMI": add_ndmi,
}


def get_sentinel_collection(aoi, data_inicio, data_fim, indice):
    """Monta a coleção Sentinel-2 já escalonada e com o índice escolhido."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(str(data_inicio), str(data_fim))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        .map(preparar_imagem)
    )

    collection = collection.map(INDEX_FUNCTIONS[indice])
    return collection


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Configurações")

data_inicio = st.sidebar.date_input("Data início")
data_fim = st.sidebar.date_input("Data fim")

indice = st.sidebar.selectbox("Índice", ["NDVI", "NDRE", "NDMI"])

if "mostrar_mapa" not in st.session_state:
    st.session_state["mostrar_mapa"] = False

if st.sidebar.button("Gerar mapa"):
    st.session_state["mostrar_mapa"] = True


# =========================================================
# ABAS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "Área de estudo",
    "Índices espectrais",
    "Dados de campo",
    "Zonas de manejo",
])


# =========================================================
# TAB 1 — ÁREA DE ESTUDO
# =========================================================

with tab1:
    st.subheader("Área de estudo")

    uploaded_file = st.file_uploader(
        "Upload do limite do talhão (.zip shapefile)",
        type=["zip"],
        key="aoi_file",
    )

    if uploaded_file is not None:
        gdf = read_zip_shapefile(uploaded_file)

        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf_ee = gdf.to_crs(epsg=4326)
        else:
            gdf_ee = gdf.copy()

        aoi = ee.FeatureCollection(gdf_ee.__geo_interface__).geometry()

        centro = gdf_ee.geometry.centroid.iloc[0]
        map_center = [centro.y, centro.x]

        st.session_state["gdf_aoi"] = gdf_ee
        st.session_state["aoi"] = aoi
        st.session_state["map_center"] = map_center

        st.success("AOI carregada com sucesso.")
    else:
        aoi = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)
        map_center = [-29.67, -53.77]
        st.session_state["gdf_aoi"] = None
        st.session_state["aoi"] = aoi
        st.session_state["map_center"] = map_center
        st.warning("Usando AOI padrão.")


# Recupera AOI e centro para as demais abas
if "aoi" not in st.session_state:
    st.session_state["aoi"] = ee.Geometry.Point([-53.77, -29.67]).buffer(1000)
if "map_center" not in st.session_state:
    st.session_state["map_center"] = [-29.67, -53.77]
if "gdf_aoi" not in st.session_state:
    st.session_state["gdf_aoi"] = None

aoi = st.session_state["aoi"]
map_center = st.session_state["map_center"]
gdf_aoi = st.session_state["gdf_aoi"]


# =========================================================
# TAB 2 — ÍNDICES ESPECTRAIS
# =========================================================

with tab2:
    st.subheader("Índices espectrais")

    if not st.session_state["mostrar_mapa"]:
        st.info("Configure o período, escolha o índice e clique em 'Gerar mapa'.")
    else:
        st.write(f"Gerando {indice} de {data_inicio} até {data_fim}")

        collection = get_sentinel_collection(aoi, data_inicio, data_fim, indice)

        n_imgs = collection.size().getInfo()
        st.write(f"Imagens encontradas: {n_imgs}")

        if n_imgs == 0:
            st.warning("Nenhuma imagem encontrada para esse período.")
        else:
            img_index = collection.select(indice).mean().clip(aoi)
            rgb = collection.median().select(["B4", "B3", "B2"]).clip(aoi)

            st.session_state["img_index"] = img_index
            st.session_state["indice_atual"] = indice
            st.session_state["collection_index"] = collection

            m = folium.Map(location=map_center, zoom_start=14, tiles="OpenStreetMap")

            add_ee_layer(
                m,
                rgb,
                {"min": 0.02, "max": 0.30, "gamma": 1.2},
                "RGB",
            )

            add_ee_layer(
                m,
                img_index,
                {"min": 0, "max": 1, "palette": ["red", "yellow", "green"]},
                indice,
            )

            if gdf_aoi is not None:
                add_boundary(m, gdf_aoi)

            folium.LayerControl().add_to(m)
            st_folium(m, width=1200, height=650)


# =========================================================
# TAB 3 — DADOS DE CAMPO
# =========================================================

with tab3:
    st.subheader("Dados de campo")

    prod_file = st.file_uploader(
        "Upload mapa de produtividade (.zip shapefile)",
        type=["zip"],
        key="prod",
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
            col_prod = st.selectbox("Selecione o atributo de produtividade", col_numericas)

            gdf_prod[col_prod] = gdf_prod[col_prod].astype(float)
            valores_brutos = gdf_prod[col_prod].dropna()

            st.write("### Estatísticas brutas")
            st.write(basic_stats(gdf_prod, col_prod))

            usar_filtro = st.checkbox(
                "Filtrar manualmente valores discrepantes antes da visualização",
                value=True,
            )

            if usar_filtro:
                min_filtro = st.number_input(
                    "Valor mínimo aceito",
                    value=float(valores_brutos.min()),
                )
                max_filtro = st.number_input(
                    "Valor máximo aceito",
                    value=float(valores_brutos.max()),
                )
                gdf_prod_filtrado = filter_by_range(
                    gdf_prod,
                    col_prod,
                    min_filtro,
                    max_filtro,
                )
            else:
                gdf_prod_filtrado = gdf_prod.copy()

            st.session_state["gdf_prod_filtrado"] = gdf_prod_filtrado
            st.session_state["col_prod"] = col_prod

            st.write(f"Pontos brutos: {len(gdf_prod)}")
            st.write(f"Pontos após filtro: {len(gdf_prod_filtrado)}")

            st.write("### Estatísticas após filtro")
            st.write(basic_stats(gdf_prod_filtrado, col_prod))

            # -------------------------------------------------
            # MAPA DE PRODUTIVIDADE FILTRADA
            # -------------------------------------------------
            st.write("### Mapa de produtividade filtrada")

            vmin = float(gdf_prod_filtrado[col_prod].min())
            vmax = float(gdf_prod_filtrado[col_prod].max())
            colormap = linear.RdYlGn_11.scale(vmin, vmax)
            colormap.caption = f"Produtividade ({col_prod})"

            m2 = folium.Map(location=map_center, zoom_start=14, tiles="OpenStreetMap")

            gdf_map = gdf_prod_filtrado.copy()
            if gdf_map.crs is not None and gdf_map.crs.to_epsg() != 4326:
                gdf_map = gdf_map.to_crs(epsg=4326)

            for _, row in gdf_map.iterrows():
                valor = row[col_prod]
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=2,
                    color=colormap(valor),
                    fill=True,
                    fill_color=colormap(valor),
                    fill_opacity=0.7,
                    weight=0,
                    popup=f"{col_prod}: {valor:.2f}",
                ).add_to(m2)

            colormap.add_to(m2)

            if gdf_aoi is not None:
                add_boundary(m2, gdf_aoi)

            folium.LayerControl().add_to(m2)
            st_folium(m2, height=550)

            # -------------------------------------------------
            # CLASSES PRELIMINARES NOS PONTOS
            # -------------------------------------------------
            st.write("### Classes preliminares de produtividade")

            gdf_classes, q33, q66 = classify_quantiles_points(
                gdf_prod_filtrado.copy(),
                col_prod,
            )

            st.write(f"Baixa ≤ {q33:.2f}")
            st.write(f"Média: {q33:.2f} a {q66:.2f}")
            st.write(f"Alta > {q66:.2f}")
            st.write(gdf_classes["classe_prod"].value_counts())

            m3 = folium.Map(location=map_center, zoom_start=14, tiles="OpenStreetMap")

            gdf_classes_map = gdf_classes.copy()
            if gdf_classes_map.crs is not None and gdf_classes_map.crs.to_epsg() != 4326:
                gdf_classes_map = gdf_classes_map.to_crs(epsg=4326)

            cores = {"Baixa": "red", "Média": "yellow", "Alta": "green"}

            for classe, cor in cores.items():
                subset = gdf_classes_map[gdf_classes_map["classe_prod"] == classe]
                for _, row in subset.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=2,
                        color=cor,
                        fill=True,
                        fill_color=cor,
                        fill_opacity=0.7,
                        weight=0,
                        popup=f"{classe} | {col_prod}: {row[col_prod]:.2f}",
                    ).add_to(m3)

            if gdf_aoi is not None:
                add_boundary(m3, gdf_aoi)

            folium.LayerControl().add_to(m3)
            st_folium(m3, height=550)

            # -------------------------------------------------
            # INTERPOLAÇÃO PRODUTIVIDADE
            # -------------------------------------------------
            st.write("### Interpolação IDW da produtividade filtrada")

            resolucao_idw = st.slider(
                "Resolução da interpolação IDW (m)",
                min_value=5,
                max_value=30,
                value=10,
                step=5,
            )

            power_idw = st.slider(
                "Potência do IDW",
                min_value=1,
                max_value=4,
                value=2,
                step=1,
            )

            if st.button("Gerar interpolação IDW da produtividade"):
                grid_x, grid_y, grid_z, gdf_idw = idw_interpolation(
                    gdf_prod_filtrado,
                    col_prod,
                    resolution=resolucao_idw,
                    power=power_idw,
                )

                xmin, ymin, xmax, ymax = gdf_idw.total_bounds

                st.session_state["grid_x"] = grid_x
                st.session_state["grid_y"] = grid_y
                st.session_state["grid_z"] = grid_z
                st.session_state["gdf_idw"] = gdf_idw
                st.session_state["resolucao_idw"] = resolucao_idw
                st.session_state["power_idw"] = power_idw

                st.success("Interpolação gerada com sucesso.")

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
                    vmax=vmax_idw,
                )
                gdf_idw.plot(ax=ax, markersize=2, color="black", alpha=0.4)
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
                    vmax=3,
                )
                gdf_idw.plot(ax=ax2, markersize=2, color="black", alpha=0.25)
                plt.colorbar(img2, ax=ax2, ticks=[1, 2, 3], label="Classe")
                ax2.set_title("Zonas preliminares de produtividade")
                ax2.set_xlabel("X (m)")
                ax2.set_ylabel("Y (m)")
                st.pyplot(fig2)

            # -------------------------------------------------
            # EXTRAÇÃO DO ÍNDICE NOS PONTOS + GRID DO ÍNDICE
            # -------------------------------------------------
            st.write("### Integração com índice espectral")

            st.caption(
                "Esta etapa extrai o índice espectral nos pontos de produtividade, "
                "anexa o índice ao GeoDataFrame e interpola o índice no mesmo padrão IDW."
            )

            max_pontos_ee = st.number_input(
                "Número máximo de pontos para extração no Earth Engine",
                min_value=500,
                max_value=5000,
                value=5000,
                step=500,
                help="Limite de segurança para evitar erro de mais de 5000 elementos no getInfo().",
            )

            if st.button("Extrair índice nos pontos e gerar grid do índice"):
                if "img_index" not in st.session_state:
                    st.warning("Gere primeiro o mapa de índice espectral na aba 'Índices espectrais'.")
                elif "gdf_prod_filtrado" not in st.session_state:
                    st.warning("Carregue e filtre primeiro o mapa de produtividade.")
                else:
                    gdf_pts = st.session_state["gdf_prod_filtrado"].copy()
                    col_prod = st.session_state["col_prod"]
                    imagem = st.session_state["img_index"]
                    indice_usado = st.session_state["indice_atual"]

                    total_pontos = len(gdf_pts)
                    if total_pontos > max_pontos_ee:
                        st.warning(
                            f"Foram encontrados {total_pontos} pontos. "
                            f"Usando amostra de {max_pontos_ee} pontos para evitar limite do Earth Engine."
                        )
                        gdf_pts = gdf_pts.sample(n=int(max_pontos_ee), random_state=42).copy()

                    gdf_pts = gdf_pts.reset_index(drop=True)
                    gdf_pts["_pid"] = np.arange(len(gdf_pts))

                    gdf_pts_ee = gdf_pts.copy()
                    if gdf_pts_ee.crs is not None and gdf_pts_ee.crs.to_epsg() != 4326:
                        gdf_pts_ee = gdf_pts_ee.to_crs(epsg=4326)

                    pontos_ee = ee.FeatureCollection(gdf_pts_ee.__geo_interface__)

                    valores = imagem.sampleRegions(
                        collection=pontos_ee,
                        scale=10,
                        geometries=False,
                    )

                    df_info = valores.limit(int(max_pontos_ee)).getInfo()
                    lista = [f["properties"] for f in df_info["features"]]
                    df_out = pd.DataFrame(lista)

                    if df_out.empty:
                        st.error("O Earth Engine não retornou valores para os pontos.")
                    elif indice_usado not in df_out.columns:
                        st.error(f"A coluna {indice_usado} não foi retornada pelo Earth Engine.")
                    else:
                        df_out = df_out.dropna(subset=[indice_usado, col_prod, "_pid"])
                        df_out["_pid"] = df_out["_pid"].astype(int)

                        st.session_state["df_prod_indice"] = df_out

                        st.write("### Dados combinados")
                        st.dataframe(df_out[["_pid", col_prod, indice_usado]].head())

                        corr = df_out[[col_prod, indice_usado]].corr().iloc[0, 1]
                        st.write("### Correlação")
                        st.write(f"Correlação ({indice_usado} x produtividade): {corr:.3f}")

                        gdf_indice = gdf_pts.merge(
                            df_out[["_pid", indice_usado]],
                            on="_pid",
                            how="inner",
                            suffixes=("", "_ee"),
                        )

                        if f"{indice_usado}_ee" in gdf_indice.columns:
                            gdf_indice[indice_usado] = gdf_indice[f"{indice_usado}_ee"]
                            gdf_indice = gdf_indice.drop(columns=[f"{indice_usado}_ee"])

                        gdf_indice = gdf_indice.dropna(subset=[indice_usado])
                        st.session_state["gdf_prod_com_indice"] = gdf_indice

                        resolution = st.session_state.get("resolucao_idw", resolucao_idw)
                        power = st.session_state.get("power_idw", power_idw)

                        grid_x_i, grid_y_i, grid_indice, gdf_idw_indice = idw_interpolation(
                            gdf_indice,
                            indice_usado,
                            resolution=resolution,
                            power=power,
                        )

                        st.session_state["grid_indice"] = grid_indice
                        st.session_state["grid_x_indice"] = grid_x_i
                        st.session_state["grid_y_indice"] = grid_y_i
                        st.session_state["gdf_idw_indice"] = gdf_idw_indice

                        st.success("Índice extraído, anexado aos pontos e interpolado com sucesso.")

                        vmin_idx = np.nanmin(grid_indice)
                        vmax_idx = np.nanmax(grid_indice)

                        fig_idx, ax_idx = plt.subplots(figsize=(8, 6))
                        img_idx = ax_idx.imshow(
                            grid_indice.T,
                            origin="lower",
                            vmin=vmin_idx,
                            vmax=vmax_idx,
                        )
                        plt.colorbar(img_idx, ax=ax_idx, label=indice_usado)
                        ax_idx.set_title(f"Interpolação IDW do {indice_usado}")
                        st.pyplot(fig_idx)

            # -------------------------------------------------
            # ANÁLISE TEMPORAL
            # -------------------------------------------------
            st.write("### Análise temporal do índice")

            if st.button("Analisar melhor data do índice"):
                gdf_pts = st.session_state["gdf_prod_filtrado"].copy()
                col_prod = st.session_state["col_prod"]

                collection = get_sentinel_collection(aoi, data_inicio, data_fim, indice)

                df_res = temporal_correlation(
                    collection=collection,
                    gdf_points=gdf_pts,
                    value_col=col_prod,
                    index_name=indice,
                    max_images=20,
                    scale=10,
                )

                st.session_state["df_temporal"] = df_res

                st.write("### Resultado")
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


# =========================================================
# TAB 4 — ZONAS DE MANEJO
# =========================================================

with tab4:
    st.subheader("Zonas de manejo")

    st.write("### Resultados disponíveis")

    if "gdf_prod_filtrado" in st.session_state:
        st.success("Produtividade filtrada disponível")
    else:
        st.warning("Produtividade ainda não carregada/filtrada")

    if "grid_z" in st.session_state:
        st.success("Interpolação IDW da produtividade disponível")
    else:
        st.warning("Interpolação IDW da produtividade ainda não gerada")

    if "grid_indice" in st.session_state:
        st.success("Grid do índice espectral disponível")
    else:
        st.warning("Grid do índice espectral ainda não gerado")

    if "df_temporal" in st.session_state:
        st.success("Análise temporal disponível")
        st.dataframe(st.session_state["df_temporal"])
    else:
        st.warning("Análise temporal ainda não realizada")

    st.write("### Zona de manejo multivariada")

    peso_prod = st.slider("Peso da produtividade", 0.0, 1.0, 0.6, 0.1)
    peso_indice = st.slider("Peso do índice espectral", 0.0, 1.0, 0.4, 0.1)

    if st.button("Gerar zona multivariada"):
        if "grid_z" not in st.session_state:
            st.warning("Execute primeiro a interpolação IDW da produtividade.")
        elif "grid_indice" not in st.session_state:
            st.warning("Extraia e interpole primeiro o índice espectral nos pontos.")
        else:
            grid_prod = st.session_state["grid_z"]
            grid_indice = st.session_state["grid_indice"]

            if grid_prod.shape != grid_indice.shape:
                st.error(
                    "Os grids de produtividade e índice possuem tamanhos diferentes. "
                    "É necessário gerar ambos com a mesma resolução e extensão."
                )
            else:
                soma_pesos = peso_prod + peso_indice

                if soma_pesos == 0:
                    st.warning("A soma dos pesos não pode ser zero.")
                else:
                    peso_prod_norm = peso_prod / soma_pesos
                    peso_indice_norm = peso_indice / soma_pesos

                    arrays = {
                        "produtividade": grid_prod,
                        "indice": grid_indice,
                    }

                    weights = {
                        "produtividade": peso_prod_norm,
                        "indice": peso_indice_norm,
                    }

                    score_grid = weighted_overlay(arrays, weights)
                    zonas_multivariadas = classify_management_zones(score_grid, n_classes=3)

                    st.session_state["score_grid"] = score_grid
                    st.session_state["zonas_multivariadas"] = zonas_multivariadas

                    st.success("Zonas multivariadas geradas com sucesso.")

                    st.write("### Score integrado")
                    fig_score, ax_score = plt.subplots(figsize=(8, 6))
                    img_score = ax_score.imshow(score_grid.T, origin="lower")
                    plt.colorbar(img_score, ax=ax_score, label="Score integrado")
                    ax_score.set_title("Score multivariado")
                    st.pyplot(fig_score)

                    st.write("### Zonas finais")
                    fig_z, ax_z = plt.subplots(figsize=(8, 6))
                    img_z = ax_z.imshow(
                        zonas_multivariadas.T,
                        origin="lower",
                        vmin=1,
                        vmax=3,
                    )
                    plt.colorbar(img_z, ax=ax_z, ticks=[1, 2, 3], label="Classe")
                    ax_z.set_title("Zona de manejo multivariada")
                    st.pyplot(fig_z)
