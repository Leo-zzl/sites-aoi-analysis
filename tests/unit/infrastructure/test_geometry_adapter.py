"""Tests for the GeometryAdapter that decouples shapely from the domain layer."""

import pytest
from shapely.geometry import Point, Polygon

from site_analysis.domain.models import Site, AOI
from site_analysis.domain.value_objects import CoverageType
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter


class TestShapelyAdapter:
    """Verify ShapelyAdapter correctly bridges WKT/str domain models to shapely objects."""

    def test_point_from_site(self):
        site = Site(name="S1", freq="F", coverage_type=CoverageType.OUTDOOR, lon=116.4, lat=39.9)
        adapter = ShapelyAdapter()
        point = adapter.point_from_site(site)
        assert isinstance(point, Point)
        assert point.x == pytest.approx(116.4)
        assert point.y == pytest.approx(39.9)

    def test_polygon_from_aoi(self):
        wkt = "POLYGON ((116 39, 117 39, 117 40, 116 40, 116 39))"
        aoi = AOI(province="P", city="C", scene="S", scene_big="SB", scene_small="SS", geometry=wkt)
        adapter = ShapelyAdapter()
        polygon = adapter.polygon_from_aoi(aoi)
        assert isinstance(polygon, Polygon)

    def test_contains_when_point_inside(self):
        wkt = "POLYGON ((116 39, 117 39, 117 40, 116 40, 116 39))"
        aoi = AOI(province="P", city="C", scene="S", scene_big="SB", scene_small="SS", geometry=wkt)
        site = Site(name="S1", freq="F", coverage_type=CoverageType.OUTDOOR, lon=116.5, lat=39.5)
        adapter = ShapelyAdapter()
        assert adapter.contains(aoi, site) is True

    def test_contains_when_point_outside(self):
        wkt = "POLYGON ((116 39, 117 39, 117 40, 116 40, 116 39))"
        aoi = AOI(province="P", city="C", scene="S", scene_big="SB", scene_small="SS", geometry=wkt)
        site = Site(name="S1", freq="F", coverage_type=CoverageType.OUTDOOR, lon=115.0, lat=39.5)
        adapter = ShapelyAdapter()
        assert adapter.contains(aoi, site) is False

    def test_wkt_roundtrip(self):
        """Loading a WKT polygon and converting back to WKT should preserve geometry."""
        original_wkt = "POLYGON ((116 39, 117 39, 117 40, 116 40, 116 39))"
        aoi = AOI(province="P", city="C", scene="S", scene_big="SB", scene_small="SS", geometry=original_wkt)
        adapter = ShapelyAdapter()
        polygon = adapter.polygon_from_aoi(aoi)
        assert polygon.wkt == original_wkt
