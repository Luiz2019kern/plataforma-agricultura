import numpy as np


def classify_quantiles_points(gdf, value_col):
    gdf = gdf.copy()

    q33 = gdf[value_col].quantile(0.33)
    q66 = gdf[value_col].quantile(0.66)

    def classificar(valor):
        if valor <= q33:
            return "Baixa"
        elif valor <= q66:
            return "Média"
        else:
            return "Alta"

    gdf["classe_prod"] = gdf[value_col].apply(classificar)

    return gdf, q33, q66


def classify_quantiles_grid(grid):
    valid = grid[~np.isnan(grid)]

    q33 = np.quantile(valid, 0.33)
    q66 = np.quantile(valid, 0.66)

    zonas = np.full(grid.shape, np.nan)

    zonas[grid <= q33] = 1
    zonas[(grid > q33) & (grid <= q66)] = 2
    zonas[grid > q66] = 3

    return zonas, q33, q66


def normalize_array(arr):
    arr = np.array(arr, dtype=float)

    arr_min = np.nanmin(arr)
    arr_max = np.nanmax(arr)

    if arr_max == arr_min:
        return np.zeros_like(arr)

    return (arr - arr_min) / (arr_max - arr_min)


def weighted_overlay(arrays, weights):
    result = None

    for key, arr in arrays.items():
        norm = normalize_array(arr)
        peso = weights.get(key, 0)

        if result is None:
            result = norm * peso
        else:
            result += norm * peso

    return result


def classify_management_zones(score_grid, n_classes=3):
    valid = score_grid[~np.isnan(score_grid)]

    if n_classes == 3:
        q33 = np.quantile(valid, 0.33)
        q66 = np.quantile(valid, 0.66)

        zonas = np.full(score_grid.shape, np.nan)

        zonas[score_grid <= q33] = 1
        zonas[(score_grid > q33) & (score_grid <= q66)] = 2
        zonas[score_grid > q66] = 3

        return zonas

    thresholds = np.quantile(
        valid,
        np.linspace(0, 1, n_classes + 1)[1:-1]
    )

    zonas = np.digitize(score_grid, thresholds) + 1
    zonas[np.isnan(score_grid)] = np.nan

    return zonas
