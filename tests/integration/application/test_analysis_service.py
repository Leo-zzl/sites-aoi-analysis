"""Integration test comparing DDD implementation against Golden Master."""

from pathlib import Path

import pandas as pd
import pytest

from tests.integration.legacy_reference import run_legacy_analysis

AOI_PATH = Path("tests/fixtures/sample_data/test_aoi_data.xlsx")
SITE_PATH = Path("tests/fixtures/sample_data/test_site_data.xlsx")
GOLDEN_MASTER_PATH = Path("tests/fixtures/sample_data/golden_master.xlsx")


def load_or_generate_golden_master() -> pd.DataFrame:
    if GOLDEN_MASTER_PATH.exists():
        return pd.read_excel(GOLDEN_MASTER_PATH)
    df = run_legacy_analysis(AOI_PATH, SITE_PATH)
    df.to_excel(GOLDEN_MASTER_PATH, index=False)
    return df


@pytest.fixture(scope="module")
def golden_master():
    return load_or_generate_golden_master()


class TestAnalysisService:
    """Integration tests for the DDD analysis service."""

    def test_analysis_matches_golden_master(self, golden_master):
        from site_analysis.application.analysis_service import SiteAnalysisService
        from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
        from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository
        from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

        aoi_repo = ExcelAoiRepository(AOI_PATH)
        site_repo = ExcelSiteRepository(SITE_PATH)
        exporter = ExcelResultExporter()

        service = SiteAnalysisService(aoi_repo, site_repo, exporter)
        result = service.run()
        result_df = result.to_dataframe()

        # 1. 行数一致
        assert len(result_df) == len(golden_master)

        # 2. 关键统计指标一致
        assert (result_df["AOI匹配状态"] == "已匹配").sum() == (golden_master["AOI匹配状态"] == "已匹配").sum()
        assert result_df["最近室外站_距离_米"].notna().sum() == golden_master["最近室外站_距离_米"].notna().sum()

        # 3. 列集合一致（顺序可以不同）
        assert set(result_df.columns) == set(golden_master.columns)

        # 4. 逐行逐列对比（按索引对齐）
        for col in golden_master.columns:
            gm_col = golden_master[col]
            res_col = result_df[col]

            if gm_col.dtype == "float64" or gm_col.dtype == "int64":
                # 数值型使用近似相等
                pd.testing.assert_series_equal(
                    gm_col.fillna(-1).sort_index(),
                    res_col.fillna(-1).sort_index(),
                    check_names=False,
                    check_dtype=False,
                )
            else:
                # 字符串型直接对比
                pd.testing.assert_series_equal(
                    gm_col.fillna("").astype(str).sort_index(),
                    res_col.fillna("").astype(str).sort_index(),
                    check_names=False,
                    check_dtype=False,
                )
