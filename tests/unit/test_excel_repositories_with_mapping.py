"""Unit tests for Excel repositories with explicit column mapping."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from site_analysis.domain.value_objects import ColumnMapping, CoverageType


class TestExcelAoiRepositoryWithMapping:
    """Test Excel AOI repository with column mapping."""

    def test_load_all_with_mapping(self):
        from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository

        df = pd.DataFrame({
            "场景名": ["商业区", "住宅区"],
            "边界WKT": [
                "POLYGON((0 0,1 0,1 1,0 1,0 0))",
                "POLYGON((2 2,3 2,3 3,2 3,2 2))",
            ],
            "备注": ["a", "b"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            mapping = ColumnMapping(scene_col="场景名", boundary_col="边界WKT")
            repo = ExcelAoiRepository(tmp_path, column_mapping=mapping)
            aois = repo.load_all()
            assert len(aois) == 2
            assert aois[0].scene == "商业区"
            assert aois[1].scene == "住宅区"
        finally:
            tmp_path.unlink()

    def test_backward_compatibility_without_mapping(self):
        from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository

        # Simulate old-style AOI file layout: 省,市,预留,场景,场景大类,场景小类,边界WKT
        df = pd.DataFrame({
            "省": ["广东省"],
            "市": ["深圳市"],
            "预留": ["-"],
            "场景": ["商业区"],
            "场景大类": ["城市中心"],
            "场景小类": ["核心"],
            "边界WKT": ["POLYGON((0 0,1 0,1 1,0 1,0 0))"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            repo = ExcelAoiRepository(tmp_path)
            aois = repo.load_all()
            assert len(aois) == 1
            assert aois[0].scene == "商业区"
        finally:
            tmp_path.unlink()


class TestExcelSiteRepositoryWithMapping:
    """Test Excel Site repository with column mapping."""

    def test_load_all_with_mapping(self):
        from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository

        df = pd.DataFrame({
            "站点名": ["CELL_001", "CELL_002"],
            "频段": ["2.6G", "2.1G"],
            "覆盖": ["室内", "室外"],
            "x": [113.5, 113.6],
            "y": [22.5, 22.6],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            mapping = ColumnMapping(
                name_col="站点名",
                lon_col="x",
                lat_col="y",
                freq_col="频段",
                coverage_type_col="覆盖",
            )
            repo = ExcelSiteRepository(tmp_path, column_mapping=mapping)
            sites = repo.load_all()
            assert len(sites) == 2
            assert sites[0].name == "CELL_001"
            assert sites[0].lon == 113.5
            assert sites[0].lat == 22.5
            assert sites[0].coverage_type == CoverageType.INDOOR
        finally:
            tmp_path.unlink()

    def test_backward_compatibility_without_mapping(self):
        from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository

        df = pd.DataFrame({
            "小区名称": ["CELL_001"],
            "使用频段": ["2.6G"],
            "覆盖类型": ["室外"],
            "经度": [113.5],
            "纬度": [22.5],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            repo = ExcelSiteRepository(tmp_path)
            sites = repo.load_all()
            assert len(sites) == 1
            assert sites[0].name == "CELL_001"
            assert sites[0].coverage_type == CoverageType.OUTDOOR
        finally:
            tmp_path.unlink()
