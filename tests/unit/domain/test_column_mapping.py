"""Unit tests for ColumnMapping value object."""

import pytest


class TestColumnMapping:
    """Test field mapping logic."""

    def test_create_and_get(self):
        from site_analysis.domain.value_objects import ColumnMapping

        mapping = ColumnMapping(
            name_col="小区名称",
            lon_col="经度",
            lat_col="纬度",
            freq_col="使用频段",
            coverage_type_col="覆盖类型",
            scene_col="场景",
            boundary_col="物业边界",
        )
        assert mapping.name_col == "小区名称"
        assert mapping.lon_col == "经度"
        assert mapping.scene_col == "场景"
        assert mapping.boundary_col == "物业边界"

    def test_missing_required_fields_detection(self):
        from site_analysis.domain.value_objects import ColumnMapping

        mapping = ColumnMapping(
            name_col="",
            lon_col="经度",
            lat_col="纬度",
            freq_col="使用频段",
            coverage_type_col="覆盖类型",
            scene_col="",
            boundary_col="边界WKT",
        )
        # Required for AOI: scene and boundary
        assert mapping.missing_aoi_fields() == ["scene_col"]
        # Required for Site: name, lon, lat, freq, coverage_type
        assert mapping.missing_site_fields() == ["name_col"]

    def test_all_aoi_fields_present(self):
        from site_analysis.domain.value_objects import ColumnMapping

        mapping = ColumnMapping(
            scene_col="场景",
            boundary_col="边界WKT",
        )
        assert mapping.missing_aoi_fields() == []

    def test_all_site_fields_present(self):
        from site_analysis.domain.value_objects import ColumnMapping

        mapping = ColumnMapping(
            name_col="小区名称",
            lon_col="经度",
            lat_col="纬度",
            freq_col="使用频段",
            coverage_type_col="覆盖类型",
        )
        assert mapping.missing_site_fields() == []
