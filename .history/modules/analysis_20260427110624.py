import ee
import pandas as pd


def temporal_correlation(
    collection,
    gdf_points,
    value_col,
    index_name,
    max_images=20,
    scale=10
):
    pontos_ee = ee.FeatureCollection(gdf_points.__geo_interface__)

    lista_imagens = collection.toList(collection.size())
    n = min(max_images, collection.size().getInfo())

    resultados = []

    for i in range(n):
        img = ee.Image(lista_imagens.get(i))
        data = img.date().format("YYYY-MM-dd").getInfo()

        amostras = img.select(index_name).sampleRegions(
            collection=pontos_ee,
            scale=scale,
            geometries=False
        )

        info = amostras.getInfo()
        lista = [f["properties"] for f in info["features"]]

        df = pd.DataFrame(lista)

        if index_name in df.columns and value_col in df.columns:
            corr = df[[value_col, index_name]].corr().iloc[0, 1]

            resultados.append({
                "data": data,
                "correlacao": corr
            })

    return pd.DataFrame(resultados)