"""Unit tests for CSV repositories with column mapping."""

import tempfile
from pathlib import Path

import pytest

from site_analysis.domain.value_objects import ColumnMapping, CoverageType


class TestCsvAoiRepository:
    """Test CSV AOI repository with column mapping."""

    def test_load_all_with_mapping(self):
        from site_analysis.infrastructure.repositories.csv_aoi_repo import CsvAoiRepository

        csv_content = "场景名称,边界,备注\n商业区,\"POLYGON((0 0,1 0,1 1,0 1,0 0))\",test\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            tmp_path = Path(f.name)

        try:
            mapping = ColumnMapping(scene_col="场景名称", boundary_col="边界")
            repo = CsvAoiRepository(tmp_path, column_mapping=mapping)
            aois = repo.load_all()
            assert len(aois) == 1
            assert aois[0].scene == "商业区"
            assert aois[0].geometry is not None
        finally:
            tmp_path.unlink()

    def test_skip_invalid_wkt(self):
        from site_analysis.infrastructure.repositories.csv_aoi_repo import CsvAoiRepository

        csv_content = '场景,边界\n商业区,"POLYGON((0 0,1 0,1 1,0 1,0 0))"\n无效,BAD_WKT\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            tmp_path = Path(f.name)

        try:
            mapping = ColumnMapping(scene_col="场景", boundary_col="边界")
            repo = CsvAoiRepository(tmp_path, column_mapping=mapping)
            aois = repo.load_all()
            assert len(aois) == 1
            assert aois[0].scene == "商业区"
        finally:
            tmp_path.unlink()


class TestCsvSiteRepository:
    """Test CSV Site repository with column mapping."""

    def test_load_all_with_mapping(self):
        from site_analysis.infrastructure.repositories.csv_site_repo import CsvSiteRepository

        csv_content = "站点名,lon,lat,频段,类型\nCELL_001,113.5,22.5,2.6G,室内\nCELL_002,113.6,22.6,2.1G,室外\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            tmp_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                name_col="站点名",
                lon_col="lon",
                lat_col="lat",
                freq_col="频段",
                coverage_type_col="类型",
            )
            repo = CsvSiteRepository(tmp_path, column_mapping=mapping)
            sites = repo.load_all()
            assert len(sites) == 2
            assert sites[0].name == "CELL_001"
            assert sites[0].coverage_type == CoverageType.INDOOR
            assert sites[1].coverage_type == CoverageType.OUTDOOR
        finally:
            tmp_path.unlink()

    def test_skip_invalid_coords(self):
        from site_analysis.infrastructure.repositories.csv_site_repo import CsvSiteRepository

        csv_content = "name,lon,lat,freq,type\nA,113.5,22.5,2.6G,室内\nB,abc,22.6,2.1G,室外\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            tmp_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                name_col="name",
                lon_col="lon",
                lat_col="lat",
                freq_col="freq",
                coverage_type_col="type",
            )
            repo = CsvSiteRepository(tmp_path, column_mapping=mapping)
            sites = repo.load_all()
            assert len(sites) == 1
            assert sites[0].name == "A"
        finally:
            tmp_path.unlink()
