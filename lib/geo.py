"""Geodesic distance helpers using BallTree (haversine)."""
import numpy as np
from sklearn.neighbors import BallTree

EARTH_KM = 6371.0088


def haversine_nearest(town_xy_rad: np.ndarray, target_xy_rad: np.ndarray) -> np.ndarray:
    """Return nearest-neighbour distance (km) from each town to the target set."""
    if len(target_xy_rad) == 0 or len(town_xy_rad) == 0:
        return np.full(len(town_xy_rad), np.nan)
    tree = BallTree(target_xy_rad, metric="haversine")
    dist_rad, _ = tree.query(town_xy_rad, k=1)
    return dist_rad.flatten() * EARTH_KM


def to_radians(lat_lon_df) -> np.ndarray:
    """Convert a 2-col (lat, lon) DataFrame to radians ndarray."""
    return np.deg2rad(lat_lon_df.to_numpy())
