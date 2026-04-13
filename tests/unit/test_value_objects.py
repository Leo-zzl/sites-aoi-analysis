"""Unit tests for domain value objects."""

import pytest


class TestCoverageType:
    """Test coverage type classification logic."""

    def test_indoor_values(self):
        from site_analysis.domain.value_objects import CoverageType

        indoor_values = ["室内", "室分", "室分系统", "Indoor", "indoor"]
        for val in indoor_values:
            assert CoverageType.classify(val) == CoverageType.INDOOR

    def test_outdoor_values(self):
        from site_analysis.domain.value_objects import CoverageType

        outdoor_values = ["室外", "宏站", "微站", "杆站", "Outdoor", "outdoor", "宏蜂窝", "微蜂窝"]
        for val in outdoor_values:
            assert CoverageType.classify(val) == CoverageType.OUTDOOR

    def test_unknown_values(self):
        from site_analysis.domain.value_objects import CoverageType

        unknown_values = ["", "  ", "未知", "hello", None, "混合"]
        for val in unknown_values:
            assert CoverageType.classify(val) == CoverageType.UNKNOWN


class TestUtmZone:
    """Test UTM zone calculation logic."""

    def test_guangdong_zone(self):
        from site_analysis.domain.value_objects import UtmZone

        zone = UtmZone.from_lon_lat(113.5, 22.8)
        # 113.5E falls into UTM zone 49 (108-114E)
        assert zone.epsg == "EPSG:32649"

    def test_northern_hemisphere(self):
        from site_analysis.domain.value_objects import UtmZone

        zone = UtmZone.from_lon_lat(116.4, 39.9)
        assert zone.epsg == "EPSG:32650"

    def test_southern_hemisphere(self):
        from site_analysis.domain.value_objects import UtmZone

        zone = UtmZone.from_lon_lat(116.4, -33.9)
        assert zone.epsg == "EPSG:32750"

    def test_zone_boundary(self):
        from site_analysis.domain.value_objects import UtmZone

        # 108E is zone 49 boundary, 108.1E should be zone 49
        zone = UtmZone.from_lon_lat(108.1, 30.0)
        assert zone.epsg == "EPSG:32649"
        # 114E is zone 50 boundary, 114.1E should be zone 50
        zone = UtmZone.from_lon_lat(114.1, 30.0)
        assert zone.epsg == "EPSG:32650"
