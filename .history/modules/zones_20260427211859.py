import numpy as np
import pandas as pd


def normalize_array(arr):
    arr = np.array(arr, dtype=float)

    arr_min = np.nanmin(arr)
    arr_max = np.nanmax(arr)

    if arr_max == arr_min:
        return np.zeros_like(arr)

    return (arr - arr_min) / (arr_max - arr_min)


def weighted_overlay(arrays, weights):
    """
    Combina múltiplas variáveis normalizadas por pesos.

    arrays: dict
        {
            "produtividade": grid_prod,
            "ndvi": grid_ndvi,
            "ndmi": grid_ndmi
        }

    weights: dict
        {
            "produtividade": 0.6,
            "ndvi": 0.3,
            "ndmi": 0.1
        }
    """

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
    """
    Classifica o grid integrado em zonas de manejo.
    """

    valid = score_grid[~np.isnan(score_grid)]

    if n_classes == 3:
        q1, q2 = np.quantile(valid, [0.33, 0.66])

        zonas = np.full(score_grid.shape, np.nan)

        zonas[score_grid <= q1] = 1
        zonas[(score_grid > q1) & (score_grid <= q2)] = 2
        zonas[score_grid > q2] = 3

        return zonas

    else:
        thresholds = np.quantile(valid, np.linspace(0, 1, n_classes + 1)[1:-1])
        zonas = np.digitize(score_grid, thresholds) + 1
        zonas[np.isnan(score_grid)] = np.nan

        return zonas
    
    import numpy as np


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

    if len(valid) == 0:
        return np.full(score_grid.shape, np.nan)

    if n_classes == 3:
        q1, q2 = np.quantile(valid, [0.33, 0.66])
        zonas = np.full(score_grid.shape, np.nan)
        zonas[score_grid <= q1] = 1
        zonas[(score_grid > q1) & (score_grid <= q2)] = 2
        zonas[score_grid > q2] = 3
        return zonas

    thresholds = np.quantile(valid, np.linspace(0, 1, n_classes + 1)[1:-1])
    zonas = np.digitize(score_grid, thresholds) + 1
    zonas[np.isnan(score_grid)] = np.nan
    return zonas
