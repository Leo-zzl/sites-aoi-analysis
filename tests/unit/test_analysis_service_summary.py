"""Unit tests for AnalysisService summary integration."""

from pathlib import Path

import pytest

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import AnalysisResult, AnalysisSummary, CoverageType

AOI_PATH = Path("tests/fixtures/sample_data/test_aoi_data.xlsx")
SITE_PATH = Path("tests/fixtures/sample_data/test_site_data.xlsx")


class TestAnalysisServiceSummary:
    """Test that AnalysisService returns a summary."""

    def test_run_returns_summary(self):
        from site_analysis.application.analysis_service import SiteAnalysisService
        from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
        from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository
        from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

        aoi_repo = ExcelAoiRepository(AOI_PATH)
        site_repo = ExcelSiteRepository(SITE_PATH)
        exporter = ExcelResultExporter()

        service = SiteAnalysisService(aoi_repo, site_repo, exporter)
        result = service.run()

        assert hasattr(result, "summary")
        assert isinstance(result.summary, AnalysisSummary)
        assert result.summary.total_sites == len(result.sites)

    def test_summary_calculation_with_manual_sites(self):
        from site_analysis.application.analysis_service import SiteAnalysisService
        from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

        # Use mock repositories to avoid file I/O
        class MockAoiRepo:
            def load_all(self):
                return []

        class MockSiteRepo:
            def load_all(self):
                return [
                    Site(name="i1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
                    Site(name="o1", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
                    Site(name="i2", freq="700M", coverage_type=CoverageType.INDOOR, lon=113.2, lat=22.2),
                ]

        service = SiteAnalysisService(MockAoiRepo(), MockSiteRepo(), ExcelResultExporter())
        result = service.run()

        assert result.summary.total_sites == 3
        assert result.summary.indoor_sites == 2
        assert result.summary.outdoor_sites == 1
