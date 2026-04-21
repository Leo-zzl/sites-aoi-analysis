"""Application service that runs the full AOI matching + nearest outdoor analysis."""

from typing import List

import geopandas as gpd
import numpy as np
import pandas as pd

from site_analysis.domain.models import AOI, Site
from site_analysis.domain.value_objects import AnalysisResult, AnalysisSummary, UtmZone
from site_analysis.infrastructure.geo.projection import project_sites_to_utm
from site_analysis.infrastructure.geo.spatial_index import SpatialIndex
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter
from site_analysis.domain.repositories import AoiRepository, SiteRepository
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

MAX_SEARCH_DISTANCE = 1000.0


class SiteAnalysisService:
    """Orchestrates spatial analysis for telecom site planning."""

    def __init__(
        self,
        aoi_repo: AoiRepository,
        site_repo: SiteRepository,
        exporter: ExcelResultExporter,
        progress_callback=None,
    ):
        self.aoi_repo = aoi_repo
        self.site_repo = site_repo
        self.exporter = exporter
        self.progress_callback = progress_callback or (lambda stage, msg, detail: None)

    def run(self) -> "AnalysisResultContainer":
        self.progress_callback(5, "准备分析...", "")

        self.progress_callback(10, "加载 AOI 数据...", "正在读取文件...")
        aois = self.aoi_repo.load_all()
        self.progress_callback(15, "加载 AOI 数据...", f"已识别 {len(aois)} 个有效 AOI")

        self.progress_callback(25, "加载站点数据...", "正在读取文件...")
        sites = self.site_repo.load_all()
        indoor_count = sum(1 for s in sites if s.is_indoor)
        outdoor_count = sum(1 for s in sites if s.is_outdoor)
        self.progress_callback(30, "加载站点数据...", f"已识别 {len(sites)} 个站点（室内 {indoor_count} / 室外 {outdoor_count}）")

        self.progress_callback(40, "执行 AOI 空间匹配...", f"构建空间数据...（{len(sites)} 个站点 / {len(aois)} 个 AOI）")
        self._match_aois(aois, sites)
        matched = sum(1 for s in sites if s.result and s.result.aoi_matched)
        self.progress_callback(55, "执行 AOI 空间匹配...", f"已完成，{matched}/{len(sites)} 个站点已匹配 AOI")

        self.progress_callback(60, "查找最近室外站...", "")
        self._find_nearest_outdoor(sites)

        self.progress_callback(85, "生成统计摘要...", "")
        summary = AnalysisSummary.from_sites(sites)
        self.progress_callback(95, "整理结果...", "")
        self.progress_callback(100, "分析完成", f"总站点数: {summary.total_sites} | AOI已匹配: {summary.aoi_matched}")
        return AnalysisResultContainer(sites, summary=summary)

    @staticmethod
    def _match_aois(aois: List[AOI], sites: List[Site]) -> None:
        if not aois or not sites:
            return

        # Build GeoDataFrames for spatial join (adapter converts domain WKT to shapely)
        adapter = ShapelyAdapter()
        site_gdf = gpd.GeoDataFrame(
            {"site_idx": range(len(sites))},
            geometry=[adapter.point_from_site(s) for s in sites],
            crs="EPSG:4326",
        )
        aoi_gdf = gpd.GeoDataFrame(
            {
                "aoi_province": [a.province for a in aois],
                "aoi_city": [a.city for a in aois],
                "aoi_scene": [a.scene for a in aois],
                "aoi_scene_big": [a.scene_big for a in aois],
                "aoi_scene_small": [a.scene_small for a in aois],
            },
            geometry=[adapter.polygon_from_aoi(a) for a in aois],
            crs="EPSG:4326",
        )

        joined = gpd.sjoin(site_gdf, aoi_gdf, how="left", predicate="within")
        joined = joined[~joined.index.duplicated(keep="first")]

        for site_idx, row in joined.iterrows():
            site = sites[int(site_idx)]
            if pd.notna(row.get("aoi_scene")):
                site.result = AnalysisResult(
                    aoi_province=str(row.get("aoi_province", "")),
                    aoi_city=str(row.get("aoi_city", "")),
                    aoi_scene=str(row.get("aoi_scene", "")),
                    aoi_scene_big=str(row.get("aoi_scene_big", "")),
                    aoi_scene_small=str(row.get("aoi_scene_small", "")),
                    aoi_matched=True,
                )

    def _find_nearest_outdoor(self, sites: List[Site]) -> None:
        indoor_sites = [s for s in sites if s.is_indoor]
        outdoor_sites = [s for s in sites if s.is_outdoor]

        if not indoor_sites or not outdoor_sites:
            self.progress_callback(70, "查找最近室外站...", "无室内站或室外站，跳过此步骤")
            return

        self.progress_callback(62, "查找最近室外站...", f"筛选室内/室外站点... 室内 {len(indoor_sites)} 个，室外 {len(outdoor_sites)} 个")

        # Determine UTM zone from median centroid
        median_lon = np.median([s.lon for s in sites])
        median_lat = np.median([s.lat for s in sites])
        utm_zone = UtmZone.from_lon_lat(median_lon, median_lat)

        self.progress_callback(65, "查找最近室外站...", f"投影坐标到 {utm_zone.epsg}...")
        indoor_coords = project_sites_to_utm(indoor_sites, utm_zone)
        outdoor_coords = project_sites_to_utm(outdoor_sites, utm_zone)

        self.progress_callback(68, "查找最近室外站...", f"构建室外站空间索引...（{len(outdoor_sites)} 个站点）")
        index = SpatialIndex.from_sites(outdoor_coords)

        self.progress_callback(72, "查找最近室外站...", f"批量查询最近室外站...（{len(indoor_sites)} 个室内站）")
        distances, indices = index.query_nearest(indoor_coords, max_distance=MAX_SEARCH_DISTANCE)

        self.progress_callback(75, "查找最近室外站...", "写入最近室外站结果...")
        found_count = 0
        for i, indoor in enumerate(indoor_sites):
            idx = indices[i]
            if idx >= 0:
                found_count += 1
                nearest = outdoor_sites[idx]
                indoor.result = AnalysisResult(
                    aoi_province=indoor.result.aoi_province,
                    aoi_city=indoor.result.aoi_city,
                    aoi_scene=indoor.result.aoi_scene,
                    aoi_scene_big=indoor.result.aoi_scene_big,
                    aoi_scene_small=indoor.result.aoi_scene_small,
                    aoi_matched=indoor.result.aoi_matched,
                    nearest_outdoor_name=nearest.name,
                    nearest_outdoor_freq=nearest.freq,
                    nearest_outdoor_distance_m=float(distances[i]),
                )
        self.progress_callback(78, "查找最近室外站...", f"已完成，{found_count}/{len(indoor_sites)} 个室内站找到最近室外站")


class AnalysisResultContainer:
    """Wrapper around the analysis output."""

    def __init__(self, sites: List[Site], summary: AnalysisSummary = None):
        self.sites = sites
        self.summary = summary or AnalysisSummary.from_sites(sites)

    def to_dataframe(self):
        exporter = ExcelResultExporter()
        return exporter.to_dataframe(self.sites)
