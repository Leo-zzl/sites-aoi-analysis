"""AOI coverage analyzer for Issue #3.

Provides two analysis modes:
1. Indoor coverage per AOI (by frequency band)
2. Outdoor macro coverage around AOI (by distance tier and frequency band)

Note: Full DIS/DAS classification and azimuth sector analysis require
additional input columns not present in the current data model.
This baseline implementation provides distance-based coverage statistics.
"""

from typing import List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from site_analysis.domain.models import AOI, Site
from site_analysis.domain.value_objects import UtmZone
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter


DEFAULT_DISTANCE_TIERS = [200, 500, 1000]


class AoiCoverageAnalyzer:
    """Analyzes indoor and outdoor coverage per AOI."""

    def analyze_indoor_coverage(
        self, aois: List[AOI], sites: List[Site]
    ) -> pd.DataFrame:
        """Return indoor site counts per AOI, grouped by frequency band."""
        adapter = ShapelyAdapter()
        indoor_sites = [s for s in sites if s.is_indoor]

        if not indoor_sites or not aois:
            return pd.DataFrame()

        # Build GeoDataFrames
        aoi_gdf = gpd.GeoDataFrame(
            {"aoi_scene": [a.scene for a in aois]},
            geometry=[adapter.polygon_from_aoi(a) for a in aois],
            crs="EPSG:4326",
        )
        site_gdf = gpd.GeoDataFrame(
            {
                "name": [s.name for s in indoor_sites],
                "freq": [s.freq for s in indoor_sites],
            },
            geometry=[adapter.point_from_site(s) for s in indoor_sites],
            crs="EPSG:4326",
        )

        # Spatial join: find indoor sites inside each AOI
        joined = gpd.sjoin(site_gdf, aoi_gdf, how="inner", predicate="within")

        rows = []
        for aoi in aois:
            aoi_name = aoi.scene
            subset = joined[joined["aoi_scene"] == aoi_name]
            freq_counts = subset["freq"].value_counts().to_dict()
            row = {
                "AOI名称": aoi_name,
                "室内站总数": len(subset),
            }
            for freq, count in sorted(freq_counts.items()):
                row[f"室内_{freq}"] = count
            rows.append(row)

        return pd.DataFrame(rows)

    def analyze_outdoor_coverage(
        self,
        aois: List[AOI],
        sites: List[Site],
        distance_tiers: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Return outdoor site counts per AOI by distance tier and frequency band.

        Distance is measured from the AOI polygon boundary (not centroid).
        """
        if distance_tiers is None:
            distance_tiers = DEFAULT_DISTANCE_TIERS

        adapter = ShapelyAdapter()
        outdoor_sites = [s for s in sites if s.is_outdoor]

        if not outdoor_sites or not aois:
            return pd.DataFrame()

        # Determine a single UTM zone from the median AOI centroid
        adapter = ShapelyAdapter()
        centroids = [adapter.polygon_from_aoi(a).centroid for a in aois]
        median_lon = np.median([c.x for c in centroids])
        median_lat = np.median([c.y for c in centroids])
        utm_zone = UtmZone.from_lon_lat(median_lon, median_lat)

        # Build GeoDataFrames and project to UTM
        aoi_gdf = gpd.GeoDataFrame(
            {"aoi_scene": [a.scene for a in aois]},
            geometry=[adapter.polygon_from_aoi(a) for a in aois],
            crs="EPSG:4326",
        ).to_crs(utm_zone.epsg)

        site_gdf = gpd.GeoDataFrame(
            {
                "name": [s.name for s in outdoor_sites],
                "freq": [s.freq for s in outdoor_sites],
            },
            geometry=[adapter.point_from_site(s) for s in outdoor_sites],
            crs="EPSG:4326",
        ).to_crs(utm_zone.epsg)

        rows = []
        for _, aoi_row in aoi_gdf.iterrows():
            aoi_name = aoi_row["aoi_scene"]
            aoi_poly = aoi_row.geometry

            # Compute distance from each outdoor site to AOI polygon boundary
            dists = site_gdf.distance(aoi_poly)

            row = {"AOI名称": aoi_name}
            for i, tier in enumerate(distance_tiers):
                if i == 0:
                    mask = dists <= tier
                    label_prefix = f"0-{tier}m"
                else:
                    prev = distance_tiers[i - 1]
                    mask = (dists > prev) & (dists <= tier)
                    label_prefix = f"{prev}-{tier}m"

                subset = site_gdf[mask]
                freq_counts = subset["freq"].value_counts().to_dict()
                for freq, count in sorted(freq_counts.items()):
                    row[f"周边_{label_prefix}_{freq}"] = count

            rows.append(row)

        return pd.DataFrame(rows)
