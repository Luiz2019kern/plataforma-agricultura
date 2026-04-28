import geopandas as gpd
import pandas as pd
import tempfile
import streamlit as st


@st.cache_data
def read_zip_shapefile(uploaded_file):
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = f"{tmpdir}/arquivo.zip"

        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        gdf = gpd.read_file(zip_path)

        if gdf.crs is not None:
            gdf = gdf.to_crs(epsg=4326)

    return gdf

@st.cache_data
def basic_stats(gdf, col):
    valores = pd.to_numeric(gdf[col], errors="coerce").dropna()
    return valores.describe()


def get_numeric_columns(gdf):
    return gdf.select_dtypes(include=["float64", "int64"]).columns


def filter_by_range(gdf, col, min_value, max_value):
    gdf = gdf.copy()
    gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    return gdf[
        (gdf[col] >= min_value) &
        (gdf[col] <= max_value)
    ].copy()


def basic_stats(gdf, col):
    valores = pd.to_numeric(gdf[col], errors="coerce").dropna()
    return valores.describe()