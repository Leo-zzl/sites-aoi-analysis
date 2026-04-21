"""CSV-backed AOI repository."""

from pathlib import Path
from typing import List, Optional

import pandas as pd
from site_analysis.domain.models import AOI
from site_analysis.domain.value_objects import ColumnMapping
from site_analysis.domain.repositories import AoiRepository
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter


def _read_csv_with_fallback_encoding(file_path: Path) -> pd.DataFrame:
    """Read CSV trying utf-8-sig first, then gbk."""
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="gbk")


class CsvAoiRepository(AoiRepository):
    """Load AOI records from a CSV file using explicit column mapping."""

    def __init__(self, file_path: Path, column_mapping: Optional[ColumnMapping] = None):
        self.file_path = file_path
        self.column_mapping = column_mapping

    def load_all(self) -> List[AOI]:
        df = _read_csv_with_fallback_encoding(self.file_path)
        aois = []

        if self.column_mapping is None:
            raise ValueError("CSV AOI repository requires a column_mapping")

        scene_col = self.column_mapping.scene_col
        boundary_col = self.column_mapping.boundary_col

        adapter = ShapelyAdapter()
        for _, row in df.iterrows():
            wkt_str = str(row.get(boundary_col, "")).strip()
            wkt_str = wkt_str.strip('"').strip("'").strip()
            if not wkt_str or wkt_str.lower() == "nan":
                continue
            if not adapter.validate_wkt(wkt_str):
                continue
            aois.append(
                AOI(
                    province="",
                    city="",
                    scene=str(row.get(scene_col, "")).strip(),
                    scene_big="",
                    scene_small="",
                    geometry=wkt_str,
                )
            )
        return aois
