"""Tests for Issue #2: large file upload support and raw-field preservation."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from site_analysis.interfaces.api import app
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository
from site_analysis.domain.value_objects import ColumnMapping


@pytest.fixture
def client():
    return TestClient(app)


class TestUploadLimit:
    def test_upload_500mb_file_accepted(self, client, tmp_path: Path):
        """A 500MB file should not be rejected by the old 50MB limit."""
        big_file = tmp_path / "big.csv"
        # Write a ~500MB CSV-like file; pd.read_csv(..., nrows=0) will treat it as one column.
        with big_file.open("wb") as f:
            f.write(b"x\n" * (500 * 1024 * 1024 // 2))

        with big_file.open("rb") as f:
            res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("big.csv", f)})

        # Must NOT be rejected by the size limit.
        assert "50MB" not in res.text, "Should not mention old 50MB limit"
        assert "500MB" not in res.text, "Should not be rejected at exactly 500MB"

    def test_upload_over_500mb_rejected(self, client, tmp_path: Path):
        """A file slightly over 500MB should be rejected."""
        huge_file = tmp_path / "huge.xlsx"
        huge_file.write_bytes(b"x" * (500 * 1024 * 1024 + 1))

        with huge_file.open("rb") as f:
            res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("huge.xlsx", f)})

        data = res.json()
        assert "error" in data
        assert "500MB" in data["error"]


class TestColumnPruning:
    def test_site_repo_reads_only_needed_columns(self, tmp_path: Path):
        """Repository should only read mapped columns + record source row."""
        df = pd.DataFrame({
            "小区名称": ["S1", "S2"],
            "经度": [116.0, 117.0],
            "纬度": [39.0, 40.0],
            "使用频段": ["2.6G", "4.9G"],
            "覆盖类型": ["室内", "室外"],
            "无用列A": ["a", "b"],
            "无用列B": [1, 2],
        })
        file_path = tmp_path / "sites.xlsx"
        df.to_excel(file_path, index=False)

        mapping = ColumnMapping(
            name_col="小区名称",
            lon_col="经度",
            lat_col="纬度",
            freq_col="使用频段",
            coverage_type_col="覆盖类型",
        )
        repo = ExcelSiteRepository(file_path, column_mapping=mapping)
        sites = repo.load_all()

        assert len(sites) == 2
        # extra_data should be empty because we only read needed columns
        # BUT _source_row must be present for later merge
        assert "_source_row" in sites[0].extra_data
        assert sites[0].extra_data["_source_row"] == 0
        assert sites[1].extra_data["_source_row"] == 1


class TestRawFieldMerge:
    def test_exporter_merges_analysis_results_with_raw_fields(self, tmp_path: Path):
        """Exporter should merge results back into the original raw file."""
        raw_df = pd.DataFrame({
            "小区名称": ["S1", "S2"],
            "经度": [116.0, 117.0],
            "纬度": [39.0, 40.0],
            "使用频段": ["2.6G", "4.9G"],
            "覆盖类型": ["室内", "室外"],
            "原始字段A": ["val1", "val2"],
            "原始字段B": [10, 20],
        })
        raw_path = tmp_path / "raw.xlsx"
        raw_df.to_excel(raw_path, index=False)

        # Build sites with _source_row and some results
        from site_analysis.domain.models import Site
        from site_analysis.domain.value_objects import CoverageType, AnalysisResult

        sites = [
            Site(
                name="S1", freq="2.6G", coverage_type=CoverageType.INDOOR,
                lon=116.0, lat=39.0, extra_data={"_source_row": 0},
                result=AnalysisResult(aoi_matched=True, aoi_scene="商业区"),
            ),
            Site(
                name="S2", freq="4.9G", coverage_type=CoverageType.OUTDOOR,
                lon=117.0, lat=40.0, extra_data={"_source_row": 1},
                result=AnalysisResult(aoi_matched=False),
            ),
        ]

        exporter = ExcelResultExporter()
        output_path = tmp_path / "merged.xlsx"
        from site_analysis.domain.value_objects import AnalysisSummary
        summary = AnalysisSummary.from_sites(sites)
        exporter.export_merged_with_summary(
            sites, summary, output_path, raw_site_file=raw_path
        )

        merged = pd.read_excel(output_path, sheet_name="Results")
        assert "原始字段A" in merged.columns
        assert "原始字段B" in merged.columns
        assert "AOI匹配状态" in merged.columns
        assert "AOI_场景" in merged.columns
        assert merged.loc[0, "原始字段A"] == "val1"
        assert merged.loc[1, "AOI匹配状态"] == "未匹配"
