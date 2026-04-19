"""Unit tests for ExcelResultExporter with Summary sheet."""

import tempfile
from pathlib import Path

import pandas as pd

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import AnalysisResult, AnalysisSummary, CoverageType


class TestExcelResultExporterSummary:
    """Test exporting results with a Summary sheet."""

    def test_export_with_summary(self):
        from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

        sites = [
            Site(name="s1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
            Site(name="s2", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
        ]
        sites[0].result = AnalysisResult(aoi_matched=True, nearest_outdoor_distance_m=500.0)
        sites[1].result = AnalysisResult(aoi_matched=True)

        summary = AnalysisSummary.from_sites(sites)
        exporter = ExcelResultExporter()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            exporter.export_with_summary(sites, summary, tmp_path)

            # Verify both sheets exist
            xls = pd.ExcelFile(tmp_path)
            assert "Results" in xls.sheet_names
            assert "Summary" in xls.sheet_names

            # Verify summary content
            summary_df = pd.read_excel(tmp_path, sheet_name="Summary")
            assert any(summary_df["指标"] == "总站点数")
            assert any(summary_df["指标"] == "AOI已匹配")
            assert summary_df.loc[summary_df["指标"] == "总站点数", "数值"].iloc[0] == 2
        finally:
            tmp_path.unlink()

    def test_backward_compatibility_plain_export(self):
        from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

        sites = [
            Site(name="s1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
        ]
        exporter = ExcelResultExporter()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            exporter.export(sites, tmp_path)
            xls = pd.ExcelFile(tmp_path)
            # Old export should only have one default sheet
            assert len(xls.sheet_names) == 1
        finally:
            tmp_path.unlink()
