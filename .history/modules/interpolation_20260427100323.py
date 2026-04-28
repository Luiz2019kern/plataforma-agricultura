import numpy as np
from scipy.spatial import cKDTree


def idw_interpolation(gdf, value_col, resolution=10, power=2, k=8):

    crs_metrico = gdf.estimate_utm_crs()
    gdf_proj = gdf.to_crs(crs_metrico)

    x = gdf_proj.geometry.x.values
    y = gdf_proj.geometry.y.values
    z = gdf_proj[value_col].values

    xmin, ymin, xmax, ymax = gdf_proj.total_bounds

    grid_x, grid_y = np.mgrid[
        xmin:xmax:resolution,
        ymin:ymax:resolution
    ]

    tree = cKDTree(np.c_[x, y])

    dist, idx = tree.query(
        np.c_[grid_x.flatten(), grid_y.flatten()],
        k=k
    )

    dist[dist == 0] = 1e-10

    weights = 1 / dist**power
    weights /= weights.sum(axis=1, keepdims=True)

    grid_z = np.sum(weights * z[idx], axis=1)
    grid_z = grid_z.reshape(grid_x.shape)

    return grid_x, grid_y, grid_z, gdf_proj