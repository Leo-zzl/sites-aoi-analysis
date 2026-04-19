"""Stress tests with large datasets."""

import time
from pathlib import Path

import pytest

from site_analysis.application.analysis_service import SiteAnalysisService
from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository

AOI_PATH = Path("tests/fixtures/sample_data/stress_aoi_data.xlsx")
SITE_PATH = Path("tests/fixtures/sample_data/stress_site_data.xlsx")


@pytest.mark.slow
@pytest.mark.integration
class TestStress:
    """Stress tests for large datasets."""

    def test_100k_sites_1000_aoi(self):
        aoi_repo = ExcelAoiRepository(AOI_PATH)
        site_repo = ExcelSiteRepository(SITE_PATH)
        exporter = ExcelResultExporter()
        service = SiteAnalysisService(aoi_repo, site_repo, exporter)

        start = time.perf_counter()
        result = service.run()
        elapsed = time.perf_counter() - start

        df = result.to_dataframe()
        assert len(df) == 100_000
        print(f"\n100k sites x 1000 AOI analysis took {elapsed:.3f}s")
        # AOI spatial join may take longer with 100k sites, allow 30s
        assert elapsed < 30.0, f"Analysis took {elapsed:.2f}s, expected < 30s"
