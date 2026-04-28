import numpy as np
from scipy.spatial import cKDTree


def idw_interpolation(gdf, value_col, resolution=10, power=2):
    gdf = gdf.copy()

    crs_metrico = gdf.estimate_utm_crs()
    gdf_m = gdf.to_crs(crs_metrico)

    coords = np.array([
        [geom.x, geom.y]
        for geom in gdf_m.geometry
    ])

    values = gdf_m[value_col].astype(float).values

    xmin, ymin, xmax, ymax = gdf_m.total_bounds

    grid_x, grid_y = np.meshgrid(
        np.arange(xmin, xmax, resolution),
        np.arange(ymin, ymax, resolution)
    )

    grid_points = np.c_[grid_x.ravel(), grid_y.ravel()]

    tree = cKDTree(coords)

    distances, idx = tree.query(
        grid_points,
        k=min(8, len(coords))
    )

    distances = np.where(distances == 0, 1e-10, distances)

    weights = 1 / distances**power
    interpolated = np.sum(weights * values[idx], axis=1) / np.sum(weights, axis=1)

    grid_z = interpolated.reshape(grid_x.shape)

    return grid_x, grid_y, grid_z, gdf_m
