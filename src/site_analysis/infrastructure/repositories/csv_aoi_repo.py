"""CSV-backed AOI repository."""

from pathlib import Path
from typing import List, Optional

import pandas as pd
from site_analysis.domain.models import AOI
from site_analysis.domain.value_objects import ColumnMapping
from site_analysis.domain.repositories import AoiRepository
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter


def _read_csv_with_fallback_encoding(file_path: Path, usecols=None) -> pd.DataFrame:
    """Read CSV trying utf-8-sig first, then gbk."""
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", usecols=usecols)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="gbk", usecols=usecols)


class CsvAoiRepository(AoiRepository):
    """Load AOI records from a CSV file using explicit column mapping."""

    def __init__(self, file_path: Path, column_mapping: Optional[ColumnMapping] = None):
        self.file_path = file_path
        self.column_mapping = column_mapping

    def load_all(self) -> List[AOI]:
        if self.column_mapping is None:
            raise ValueError("CSV AOI repository requires a column_mapping")

        mapping = self.column_mapping
        cols = [mapping.scene_col, mapping.boundary_col] + list(mapping.extra_aoi_cols)
        usecols = [c for c in cols if c]
        df = _read_csv_with_fallback_encoding(self.file_path, usecols=usecols or None)
        aois = []

        adapter = ShapelyAdapter()
        for _, row in df.iterrows():
            wkt_str = str(row.get(mapping.boundary_col, "")).strip()
            wkt_str = wkt_str.strip('"').strip("'").strip()
            if not wkt_str or wkt_str.lower() == "nan":
                continue
            if not adapter.validate_wkt(wkt_str):
                continue
            extra = {}
            for col in mapping.extra_aoi_cols:
                if col in df.columns:
                    extra[col] = str(row.get(col, "")).strip()
            aois.append(
                AOI(
                    province="",
                    city="",
                    scene=str(row.get(mapping.scene_col, "")).strip(),
                    scene_big="",
                    scene_small="",
                    geometry=wkt_str,
                    extra_data=extra,
                )
            )
        return aois
