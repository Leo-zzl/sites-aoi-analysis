"""Unit tests for AnalysisSummary value object."""

import pytest

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import CoverageType


class TestAnalysisSummary:
    """Test summary statistics calculation."""

    def test_empty_sites(self):
        from site_analysis.domain.value_objects import AnalysisSummary

        summary = AnalysisSummary.from_sites([])
        assert summary.total_sites == 0
        assert summary.aoi_matched == 0
        assert summary.indoor_sites == 0
        assert summary.indoor_with_outdoor == 0

    def test_basic_calculation(self):
        from site_analysis.domain.value_objects import AnalysisSummary, AnalysisResult

        sites = [
            Site(name="s1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
            Site(name="s2", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
            Site(name="s3", freq="700M", coverage_type=CoverageType.INDOOR, lon=113.2, lat=22.2),
        ]
        # s1 matched AOI and has nearest outdoor
        sites[0].result = AnalysisResult(aoi_matched=True, nearest_outdoor_distance_m=500.0)
        # s2 matched AOI
        sites[1].result = AnalysisResult(aoi_matched=True)
        # s3 not matched, no outdoor
        sites[2].result = AnalysisResult(aoi_matched=False)

        summary = AnalysisSummary.from_sites(sites)
        assert summary.total_sites == 3
        assert summary.aoi_matched == 2
        assert summary.indoor_sites == 2
        assert summary.indoor_with_outdoor == 1
        assert summary.outdoor_sites == 1
