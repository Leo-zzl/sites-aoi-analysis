"""Coordinate projection helpers."""

from typing import List, Tuple

import numpy as np
import pyproj

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import UtmZone


def project_sites_to_utm(sites: List[Site], utm_zone: UtmZone) -> np.ndarray:
    """Project a list of sites to the given UTM zone and return an Nx2 array of (x, y)."""
    transformer = pyproj.Transformer.from_crs("EPSG:4326", utm_zone.epsg, always_xy=True)
    lons = np.array([s.lon for s in sites])
    lats = np.array([s.lat for s in sites])
    xs, ys = transformer.transform(lons, lats)
    return np.column_stack([xs, ys])
