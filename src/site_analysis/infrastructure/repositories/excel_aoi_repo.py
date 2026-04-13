"""Excel-backed AOI repository."""

from pathlib import Path
from typing import List

import pandas as pd
from shapely.wkt import loads as wkt_loads

from site_analysis.domain.models import AOI
from site_analysis.infrastructure.repositories import AoiRepository


class ExcelAoiRepository(AoiRepository):
    """Load AOI records from an Excel file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load_all(self) -> List[AOI]:
        df = pd.read_excel(self.file_path, sheet_name=0)
        aois = []
        for _, row in df.iterrows():
            wkt_str = str(row.iloc[6]).strip()
            wkt_str = wkt_str.strip('"').strip("'").strip()
            if not wkt_str or wkt_str.lower() == "nan":
                continue
            try:
                polygon = wkt_loads(wkt_str)
            except Exception:
                continue
            aois.append(
                AOI(
                    province=str(row.iloc[0]).strip(),
                    city=str(row.iloc[1]).strip(),
                    scene=str(row.iloc[3]).strip(),
                    scene_big=str(row.iloc[4]).strip(),
                    scene_small=str(row.iloc[5]).strip(),
                    geometry=polygon,
                )
            )
        return aois
