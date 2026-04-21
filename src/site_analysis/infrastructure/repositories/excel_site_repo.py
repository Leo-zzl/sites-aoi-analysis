"""Excel-backed Site repository."""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import ColumnMapping, CoverageType
from site_analysis.domain.repositories import SiteRepository

COL_SITE_NAME = "小区名称"
COL_FREQ = "使用频段"
COL_COVER_TYPE = "覆盖类型"

LAT_KEYWORDS = {"纬度", "lat", "latitude", "latitude_deg", "lat_deg", "y"}
LON_KEYWORDS = {"经度", "lon", "longitude", "longitude_deg", "lon_deg", "x"}


def _find_lat_lon_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    lat_col = lon_col = None
    for c in df.columns:
        col_clean = str(c).strip().lower().replace(" ", "").replace("_", "")
        if col_clean in LAT_KEYWORDS or any(k in col_clean for k in LAT_KEYWORDS):
            lat_col = c
        if col_clean in LON_KEYWORDS or any(k in col_clean for k in LON_KEYWORDS):
            lon_col = c
    return lat_col, lon_col


class ExcelSiteRepository(SiteRepository):
    """Load site records from an Excel file."""

    def __init__(self, file_path: Path, column_mapping: Optional[ColumnMapping] = None):
        self.file_path = file_path
        self.column_mapping = column_mapping

    def load_all(self) -> List[Site]:
        if self.column_mapping is not None:
            name_col = self.column_mapping.name_col
            lon_col = self.column_mapping.lon_col
            lat_col = self.column_mapping.lat_col
            freq_col = self.column_mapping.freq_col
            coverage_type_col = self.column_mapping.coverage_type_col
            needed_cols = [c for c in [name_col, lon_col, lat_col, freq_col, coverage_type_col] if c]
            df = pd.read_excel(self.file_path, sheet_name=0, usecols=needed_cols or None)

            df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
            df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
            valid_mask = df[lon_col].notna() & df[lat_col].notna()
            df = df[valid_mask]

            sites = []
            for original_idx, row in df.iterrows():
                sites.append(
                    Site(
                        name=str(row[name_col]),
                        freq=str(row[freq_col]),
                        coverage_type=CoverageType.classify(row[coverage_type_col]),
                        lon=float(row[lon_col]),
                        lat=float(row[lat_col]),
                        extra_data={"_source_row": int(original_idx)},
                    )
                )
            return sites

        # Legacy path: auto-detect columns
        df = pd.read_excel(self.file_path, sheet_name=0)
        for col in [COL_SITE_NAME, COL_FREQ, COL_COVER_TYPE]:
            if col not in df.columns:
                raise KeyError(f"❌ 找不到列 '{col}'")

        lat_col, lon_col = _find_lat_lon_columns(df)
        if lat_col is None or lon_col is None:
            lat_col = df.columns[3]
            lon_col = df.columns[5]

        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        valid_mask = df[lon_col].notna() & df[lat_col].notna()
        df = df[valid_mask]

        sites = []
        for original_idx, row in df.iterrows():
            extra = {
                col: row[col]
                for col in df.columns
                if col not in {COL_SITE_NAME, COL_FREQ, COL_COVER_TYPE, lat_col, lon_col}
            }
            extra["_source_row"] = int(original_idx)
            sites.append(
                Site(
                    name=str(row[COL_SITE_NAME]),
                    freq=str(row[COL_FREQ]),
                    coverage_type=CoverageType.classify(row[COL_COVER_TYPE]),
                    lon=float(row[lon_col]),
                    lat=float(row[lat_col]),
                    extra_data=extra,
                )
            )
        return sites
