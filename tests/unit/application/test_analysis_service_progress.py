"""Unit tests for SiteAnalysisService progress callbacks (P2-T01, P2-T03)."""

import pytest

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import CoverageType
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter


class MockAoiRepo:
    def load_all(self):
        return []


class MockSiteRepo:
    def __init__(self, sites):
        self.sites = sites

    def load_all(self):
        return self.sites


class TestAnalysisServiceProgress:
    def test_progress_callback_stages(self):
        from site_analysis.application.analysis_service import SiteAnalysisService

        sites = [
            Site(name="i1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
            Site(name="o1", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
        ]
        service = SiteAnalysisService(MockAoiRepo(), MockSiteRepo(sites), ExcelResultExporter())

        calls = []
        def capture(stage, message, detail=""):
            calls.append((stage, message, detail))

        service.progress_callback = capture
        service.run()

        stages = [c[0] for c in calls]
        # Should have more granular stages than before
        assert 5 in stages  # prepare
        assert any(10 <= s <= 15 for s in stages)  # AOI load
        assert any(25 <= s <= 30 for s in stages)  # site load
        assert any(40 <= s <= 55 for s in stages)  # AOI match
        assert any(60 <= s <= 78 for s in stages)  # nearest outdoor
        assert 100 in stages  # complete

        # Should contain count details
        messages_and_details = [f"{c[1]} {c[2]}" for c in calls]
        combined = " ".join(messages_and_details)
        assert "站点" in combined or "AOI" in combined

    def test_find_nearest_outdoor_substeps(self):
        from site_analysis.application.analysis_service import SiteAnalysisService

        sites = [
            Site(name="i1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
            Site(name="o1", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
        ]
        service = SiteAnalysisService(MockAoiRepo(), MockSiteRepo(sites), ExcelResultExporter())

        calls = []
        def capture(stage, message, detail=""):
            calls.append((stage, message, detail))

        service.progress_callback = capture
        service.run()

        messages_and_details = [f"{c[1]} {c[2]}" for c in calls]
        # Verify substeps in nearest outdoor search
        assert any("筛选" in m or "室内" in m for m in messages_and_details)
        assert any("投影" in m or "EPSG" in m for m in messages_and_details)
        assert any("索引" in m for m in messages_and_details)
        assert any("查询" in m or "最近室外站" in m for m in messages_and_details)
