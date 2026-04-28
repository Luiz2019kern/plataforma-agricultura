import numpy as np

def classify_quantiles_grid(grid_z):
    q33 = np.nanpercentile(grid_z, 33)
    q66 = np.nanpercentile(grid_z, 66)

    zonas_grid = np.where(
        grid_z <= q33, 1,
        np.where(grid_z <= q66, 2, 3)
    )

    return zonas_grid, q33, q66

def classify_quantiles_points(gdf, value_col):
    q33 = gdf[value_col].quantile(0.33)
    q66 = gdf[value_col].quantile(0.66)

    def classificar(valor):
        if valor <= q33:
            return "Baixa"
        elif valor <= q66:
            return "Média"
        else:
            return "Alta"

    gdf = gdf.copy()
    gdf["classe_prod"] = gdf[value_col].apply(classificar)
    
    return gdf, q33, q66