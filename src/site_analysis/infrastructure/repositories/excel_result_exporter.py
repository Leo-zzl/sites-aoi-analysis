"""Excel result exporter."""

from pathlib import Path
from typing import List

import pandas as pd

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import AnalysisResult, AnalysisSummary


class ExcelResultExporter:
    """Export analysis results to an Excel file."""

    def export(self, sites: List[Site], output_path: Path) -> None:
        rows = []
        for site in sites:
            row = {
                "AOI_省": site.result.aoi_province,
                "AOI_市": site.result.aoi_city,
                "AOI_场景": site.result.aoi_scene,
                "AOI_场景大类": site.result.aoi_scene_big,
                "AOI_场景小类": site.result.aoi_scene_small,
                "AOI匹配状态": site.result.aoi_match_status,
                "最近室外站_名称": site.result.nearest_outdoor_name,
                "最近室外站_频段": site.result.nearest_outdoor_freq,
                "最近室外站_距离_米": site.result.nearest_outdoor_distance_m,
                "小区名称": site.name,
                "使用频段": site.freq,
                "覆盖类型": self._coverage_type_str(site.coverage_type),
                "经度": site.lon,
                "纬度": site.lat,
            }
            row.update(site.extra_data)
            rows.append(row)

        df = pd.DataFrame(rows)
        front_cols = [
            "AOI_省", "AOI_市", "AOI_场景", "AOI_场景大类", "AOI_场景小类", "AOI匹配状态",
            "最近室外站_名称", "最近室外站_频段", "最近室外站_距离_米",
        ]
        other_cols = [c for c in df.columns if c not in front_cols]
        df = df[front_cols + other_cols]
        df.to_excel(output_path, index=False, engine="openpyxl")

    @staticmethod
    def _coverage_type_str(coverage_type) -> str:
        from site_analysis.domain.value_objects import CoverageType
        mapping = {
            CoverageType.INDOOR: "室内",
            CoverageType.OUTDOOR: "室外",
            CoverageType.UNKNOWN: "未知",
        }
        return mapping.get(coverage_type, "未知")

    def export_with_summary(
        self, sites: List[Site], summary: AnalysisSummary, output_path: Path
    ) -> None:
        """Export results and summary to an Excel file with two sheets."""
        df_results = self.to_dataframe(sites)
        df_summary = pd.DataFrame({
            "指标": [
                "总站点数",
                "AOI已匹配",
                "室内站总数",
                "室外站总数",
                "1000米内找到室外站",
            ],
            "数值": [
                summary.total_sites,
                summary.aoi_matched,
                summary.indoor_sites,
                summary.outdoor_sites,
                summary.indoor_with_outdoor,
            ],
        })

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="Summary", index=False)
            df_results.to_excel(writer, sheet_name="Results", index=False)

    def to_dataframe(self, sites: List[Site]) -> pd.DataFrame:
        """Return results as a DataFrame without writing to disk."""
        rows = []
        for site in sites:
            row = {
                "AOI_省": site.result.aoi_province,
                "AOI_市": site.result.aoi_city,
                "AOI_场景": site.result.aoi_scene,
                "AOI_场景大类": site.result.aoi_scene_big,
                "AOI_场景小类": site.result.aoi_scene_small,
                "AOI匹配状态": site.result.aoi_match_status,
                "最近室外站_名称": site.result.nearest_outdoor_name,
                "最近室外站_频段": site.result.nearest_outdoor_freq,
                "最近室外站_距离_米": site.result.nearest_outdoor_distance_m,
                "小区名称": site.name,
                "使用频段": site.freq,
                "覆盖类型": self._coverage_type_str(site.coverage_type),
                "经度": site.lon,
                "纬度": site.lat,
            }
            row.update(site.extra_data)
            rows.append(row)

        df = pd.DataFrame(rows)
        front_cols = [
            "AOI_省", "AOI_市", "AOI_场景", "AOI_场景大类", "AOI_场景小类", "AOI匹配状态",
            "最近室外站_名称", "最近室外站_频段", "最近室外站_距离_米",
        ]
        other_cols = [c for c in df.columns if c not in front_cols]
        return df[front_cols + other_cols]
