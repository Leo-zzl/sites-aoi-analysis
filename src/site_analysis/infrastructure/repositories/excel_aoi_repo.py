"""Excel-backed AOI repository."""

from pathlib import Path
from typing import List, Optional

import pandas as pd
from site_analysis.domain.models import AOI
from site_analysis.domain.value_objects import ColumnMapping
from site_analysis.domain.repositories import AoiRepository
from site_analysis.infrastructure.geo.geometry_adapter import ShapelyAdapter


class ExcelAoiRepository(AoiRepository):
    """Load AOI records from an Excel file."""

    def __init__(self, file_path: Path, column_mapping: Optional[ColumnMapping] = None):
        self.file_path = file_path
        self.column_mapping = column_mapping

    def load_all(self) -> List[AOI]:
        adapter = ShapelyAdapter()
        aois = []

        if self.column_mapping is not None:
            mapping = self.column_mapping
            cols = [mapping.scene_col, mapping.boundary_col] + list(mapping.extra_aoi_cols)
            usecols = [c for c in cols if c]
            df = pd.read_excel(self.file_path, sheet_name=0, usecols=usecols or None)
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

        # Legacy path: hard-coded column positions
        df = pd.read_excel(self.file_path, sheet_name=0)
        for _, row in df.iterrows():
            wkt_str = str(row.iloc[6]).strip()
            wkt_str = wkt_str.strip('"').strip("'").strip()
            if not wkt_str or wkt_str.lower() == "nan":
                continue
            if not adapter.validate_wkt(wkt_str):
                continue
            aois.append(
                AOI(
                    province=str(row.iloc[0]).strip(),
                    city=str(row.iloc[1]).strip(),
                    scene=str(row.iloc[3]).strip(),
                    scene_big=str(row.iloc[4]).strip(),
                    scene_small=str(row.iloc[5]).strip(),
                    geometry=wkt_str,
                )
            )
        return aois
