"""Spatial index using scipy cKDTree for fast nearest-neighbor queries."""

from typing import List, Optional, Tuple

import numpy as np
from scipy.spatial import cKDTree


class SpatialIndex:
    """Wrapper around cKDTree for 2D point nearest-neighbor search."""

    def __init__(self, coords: np.ndarray, payloads: Optional[List] = None):
        coords = np.asarray(coords, dtype=np.float64)

        # Filter out NaN/inf coordinates before building the tree
        valid_mask = np.isfinite(coords).all(axis=1)
        if not valid_mask.all():
            invalid_count = int((~valid_mask).sum())
            # In a CLI context this might print; in tests it's acceptable noise
            print(f"⚠️  发现 {invalid_count} 个无效坐标，已过滤")
            coords = coords[valid_mask]
            if payloads is not None:
                payloads = [p for p, m in zip(payloads, valid_mask) if m]

        if len(coords) == 0:
            raise ValueError("没有有效的坐标数据来构建空间索引")

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
            distances: array of distances (nan if no neighbor within max_distance or invalid query)
            indices: array of payload indices (-1 if no neighbor within max_distance or invalid query)
        """
        query_coords = np.asarray(query_coords, dtype=np.float64)
        n_points = len(query_coords)

        out_distances = np.full(n_points, np.nan, dtype=float)
        out_indices = np.full(n_points, -1, dtype=int)

        valid_mask = np.isfinite(query_coords).all(axis=1)
        if not valid_mask.any():
            return out_distances, out_indices

        if not valid_mask.all():
            invalid_count = int((~valid_mask).sum())
            print(f"⚠️  发现 {invalid_count} 个无效查询点（NaN/inf），将返回空结果")

        valid_coords = query_coords[valid_mask]
        distances, indices = self.tree.query(valid_coords, k=1, distance_upper_bound=max_distance)
        valid_result_mask = indices < len(self.tree.data)

        out_distances[valid_mask] = np.where(valid_result_mask, distances, np.nan)
        out_indices[valid_mask] = np.where(valid_result_mask, indices, -1)

        return out_distances, out_indices
