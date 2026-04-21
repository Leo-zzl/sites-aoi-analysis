"""CSV-backed Site repository."""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from site_analysis.domain.models import Site
from site_analysis.domain.value_objects import ColumnMapping, CoverageType
from site_analysis.domain.repositories import SiteRepository


def _read_csv_with_fallback_encoding(file_path: Path, usecols=None) -> pd.DataFrame:
    """Read CSV trying utf-8-sig first, then gbk."""
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", usecols=usecols)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="gbk", usecols=usecols)


class CsvSiteRepository(SiteRepository):
    """Load site records from a CSV file using explicit column mapping."""

    def __init__(self, file_path: Path, column_mapping: Optional[ColumnMapping] = None):
        self.file_path = file_path
        self.column_mapping = column_mapping

    def load_all(self) -> List[Site]:
        if self.column_mapping is None:
            raise ValueError("CSV Site repository requires a column_mapping")

        name_col = self.column_mapping.name_col
        lon_col = self.column_mapping.lon_col
        lat_col = self.column_mapping.lat_col
        freq_col = self.column_mapping.freq_col
        coverage_type_col = self.column_mapping.coverage_type_col
        needed_cols = [name_col, lon_col, lat_col, freq_col, coverage_type_col]

        df = _read_csv_with_fallback_encoding(self.file_path, usecols=needed_cols)
        sites = []

        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        valid_mask = df[lon_col].notna() & df[lat_col].notna()
        df = df[valid_mask]

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
