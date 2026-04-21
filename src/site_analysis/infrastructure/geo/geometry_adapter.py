"""Geometry adapter that decouples shapely from the domain layer.

Domain models (Site, AOI) hold only primitive geometry data
(lon/lat tuples and WKT strings).  This adapter converts those
primitives into shapely objects when spatial calculations are
required in the application / infrastructure layers.
"""

from typing import Protocol

from shapely.geometry import Point, Polygon
from shapely.wkt import loads as wkt_loads

from site_analysis.domain.models import AOI, Site


class GeometryAdapter(Protocol):
    """Protocol for geometry operations."""

    def point_from_site(self, site: Site) -> Point:
        ...

    def polygon_from_aoi(self, aoi: AOI) -> Polygon:
        ...

    def contains(self, aoi: AOI, site: Site) -> bool:
        ...

    def validate_wkt(self, wkt_str: str) -> bool:
        ...


class ShapelyAdapter:
    """Shapely-based implementation of GeometryAdapter."""

    def point_from_site(self, site: Site) -> Point:
        return Point(site.lon, site.lat)

    def polygon_from_aoi(self, aoi: AOI) -> Polygon:
        return wkt_loads(aoi.geometry)

    def contains(self, aoi: AOI, site: Site) -> bool:
        polygon = self.polygon_from_aoi(aoi)
        point = self.point_from_site(site)
        return bool(polygon.contains(point))

    def validate_wkt(self, wkt_str: str) -> bool:
        try:
            _ = wkt_loads(wkt_str)
            return True
        except Exception:
            return False
