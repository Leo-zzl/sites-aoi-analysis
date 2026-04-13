"""Spatial index using scipy cKDTree for fast nearest-neighbor queries."""

from typing import List, Optional, Tuple

import numpy as np
from scipy.spatial import cKDTree


class SpatialIndex:
    """Wrapper around cKDTree for 2D point nearest-neighbor search."""

    def __init__(self, coords: np.ndarray, payloads: Optional[List] = None):
        self.tree = cKDTree(coords)
        self.payloads = payloads

    @classmethod
    def from_sites(cls, projected_coords: np.ndarray, payloads: Optional[List] = None) -> "SpatialIndex":
        return cls(projected_coords, payloads)

    def query_nearest(
        self, query_coords: np.ndarray, max_distance: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Query nearest neighbor for each point in query_coords.

        Returns:
            distances: array of distances (inf if no neighbor within max_distance)
            indices: array of payload indices (-1 if no neighbor within max_distance)
        """
        distances, indices = self.tree.query(query_coords, k=1, distance_upper_bound=max_distance)
        valid_mask = indices < len(self.tree.data)
        out_distances = np.full(len(query_coords), np.nan, dtype=float)
        out_indices = np.full(len(query_coords), -1, dtype=int)
        out_distances[valid_mask] = distances[valid_mask]
        out_indices[valid_mask] = indices[valid_mask]
        return out_distances, out_indices
