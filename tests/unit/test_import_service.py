"""Unit tests for ImportService."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from site_analysis.domain.value_objects import ColumnMapping


class TestImportService:
    """Test column preview and validation logic."""

    def test_preview_columns_excel(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({"A": [1], "B": [2]})
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            cols = service.preview_columns(tmp_path)
            assert set(cols) == {"A", "B"}
        finally:
            tmp_path.unlink()

    def test_preview_columns_csv(self):
        from site_analysis.application.import_service import ImportService

        tmp_path = Path(tempfile.mktemp(suffix=".csv"))
        tmp_path.write_text("X,Y,Z\n1,2,3\n", encoding="utf-8")

        try:
            service = ImportService()
            cols = service.preview_columns(tmp_path)
            assert set(cols) == {"X", "Y", "Z"}
        finally:
            tmp_path.unlink()

    def test_validate_aoi_mapping_success(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({
            "场景名": ["商业区"],
            "边界": ["POLYGON((0 0,1 0,1 1,0 1,0 0))"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            mapping = ColumnMapping(scene_col="场景名", boundary_col="边界")
            result = service.validate_mapping(tmp_path, mapping, "aoi")
            assert result.is_valid is True
            assert len(result.preview_rows) == 1
        finally:
            tmp_path.unlink()

    def test_validate_aoi_mapping_missing_columns(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({"场景名": ["商业区"]})
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            mapping = ColumnMapping(scene_col="场景名", boundary_col="边界")
            result = service.validate_mapping(tmp_path, mapping, "aoi")
            assert result.is_valid is False
            assert any("边界" in err for err in result.errors)
        finally:
            tmp_path.unlink()

    def test_validate_aoi_mapping_invalid_wkt(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({
            "场景名": ["商业区"],
            "边界": ["BAD_WKT"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            mapping = ColumnMapping(scene_col="场景名", boundary_col="边界")
            result = service.validate_mapping(tmp_path, mapping, "aoi")
            assert result.is_valid is False
            assert any("WKT" in err for err in result.errors)
        finally:
            tmp_path.unlink()

    def test_validate_site_mapping_success(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({
            "小区": ["CELL_001"],
            "经度": [113.5],
            "纬度": [22.5],
            "频段": ["2.6G"],
            "覆盖": ["室内"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            mapping = ColumnMapping(
                name_col="小区",
                lon_col="经度",
                lat_col="纬度",
                freq_col="频段",
                coverage_type_col="覆盖",
            )
            result = service.validate_mapping(tmp_path, mapping, "site")
            assert result.is_valid is True
            assert len(result.preview_rows) == 1
        finally:
            tmp_path.unlink()

    def test_validate_site_mapping_invalid_lon_lat(self):
        from site_analysis.application.import_service import ImportService

        df = pd.DataFrame({
            "小区": ["CELL_001"],
            "经度": ["abc"],
            "纬度": ["def"],
            "频段": ["2.6G"],
            "覆盖": ["室内"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            service = ImportService()
            mapping = ColumnMapping(
                name_col="小区",
                lon_col="经度",
                lat_col="纬度",
                freq_col="频段",
                coverage_type_col="覆盖",
            )
            result = service.validate_mapping(tmp_path, mapping, "site")
            assert result.is_valid is False
            assert any("经度" in err or "纬度" in err for err in result.errors)
        finally:
            tmp_path.unlink()
