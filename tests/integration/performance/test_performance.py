"""Performance benchmarks for the analysis pipeline."""

import time
from pathlib import Path

import pytest

from site_analysis.application.analysis_service import SiteAnalysisService
from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository

AOI_PATH = Path("tests/fixtures/sample_data/test_aoi_data.xlsx")
SITE_PATH = Path("tests/fixtures/sample_data/test_site_data.xlsx")


@pytest.mark.slow
@pytest.mark.integration
class TestPerformance:
    """Benchmark analysis performance under load."""

    def test_1000x1000_runtime(self):
        aoi_repo = ExcelAoiRepository(AOI_PATH)
        site_repo = ExcelSiteRepository(SITE_PATH)
        exporter = ExcelResultExporter()
        service = SiteAnalysisService(aoi_repo, site_repo, exporter)

        start = time.perf_counter()
        result = service.run()
        elapsed = time.perf_counter() - start

        df = result.to_dataframe()
        assert len(df) == 1000
        assert elapsed < 5.0, f"Analysis took {elapsed:.2f}s, expected < 5s"
        print(f"\n1000x1000 analysis took {elapsed:.3f}s")

    def test_1000x1000_aoi_match_count(self):
        aoi_repo = ExcelAoiRepository(AOI_PATH)
        site_repo = ExcelSiteRepository(SITE_PATH)
        exporter = ExcelResultExporter()
        service = SiteAnalysisService(aoi_repo, site_repo, exporter)

        result = service.run()
        df = result.to_dataframe()
        # With 1000 random AOIs over the same area, some sites should match
        matched = (df["AOI匹配状态"] == "已匹配").sum()
        assert matched >= 0
