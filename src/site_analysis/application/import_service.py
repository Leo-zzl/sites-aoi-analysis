"""Application service for column mapping preview and validation."""

from pathlib import Path
from typing import List

import pandas as pd
from shapely.wkt import loads as wkt_loads

from site_analysis.domain.value_objects import ColumnMapping, FileType, ValidationResult


# Keyword sets for auto-detection (migrated from gui/view_model.py)
_NAME_KEYWORDS = {"小区名称", "站点名", "name", "站点名称", "小区"}
_LON_KEYWORDS = {"经度", "lon", "longitude", "x", "lng"}
_LAT_KEYWORDS = {"纬度", "lat", "latitude", "y"}
_FREQ_KEYWORDS = {"使用频段", "频段", "freq", "frequency"}
_COVERAGE_KEYWORDS = {"覆盖类型", "类型", "cover", "coverage", "covertype"}
_SCENE_KEYWORDS = {"场景", "scene", "场景名", "场景名称"}
_BOUNDARY_KEYWORDS = {"边界", "boundary", "wkt", "边界WKT", "物业边界", "polygon"}


class ImportService:
    """Orchestrates file preview and column-mapping validation."""

    @staticmethod
    def detect_column(columns: List[str], keywords: set) -> str:
        """Return the first column that matches any keyword (case-insensitive)."""
        for c in columns:
            col_clean = str(c).strip().lower().replace(" ", "").replace("_", "")
            if col_clean in keywords or any(k in col_clean for k in keywords):
                return c
        return ""

    @staticmethod
    def suggest_mapping(columns: List[str], file_type: str) -> ColumnMapping:
        """Suggest column mapping based on auto-detection keywords."""
        if file_type == "aoi":
            return ColumnMapping(
                scene_col=ImportService.detect_column(columns, _SCENE_KEYWORDS),
                boundary_col=ImportService.detect_column(columns, _BOUNDARY_KEYWORDS),
            )
        if file_type == "site":
            return ColumnMapping(
                name_col=ImportService.detect_column(columns, _NAME_KEYWORDS),
                lon_col=ImportService.detect_column(columns, _LON_KEYWORDS),
                lat_col=ImportService.detect_column(columns, _LAT_KEYWORDS),
                freq_col=ImportService.detect_column(columns, _FREQ_KEYWORDS),
                coverage_type_col=ImportService.detect_column(columns, _COVERAGE_KEYWORDS),
            )
        raise ValueError(f"Unknown file_type: {file_type}")

    @staticmethod
    def preview_columns(file_path: Path) -> List[str]:
        """Return the list of column names from the input file."""
        file_type = FileType.from_path(file_path)
        if file_type == FileType.XLSX:
            df = pd.read_excel(file_path, sheet_name=0, nrows=0)
        else:
            try:
                df = pd.read_csv(file_path, encoding="utf-8-sig", nrows=0)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="gbk", nrows=0)
        return list(df.columns)

    @staticmethod
    def validate_mapping(
        file_path: Path,
        column_mapping: ColumnMapping,
        data_type: str,
        preview_limit: int = 5,
    ) -> ValidationResult:
        """Validate a column mapping against the first N rows of a file."""
        file_type = FileType.from_path(file_path)
        if file_type == FileType.XLSX:
            df = pd.read_excel(file_path, sheet_name=0, nrows=preview_limit)
        else:
            try:
                df = pd.read_csv(file_path, encoding="utf-8-sig", nrows=preview_limit)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="gbk", nrows=preview_limit)

        file_cols = set(df.columns)

        if data_type == "aoi":
            return ImportService._validate_aoi(df, file_cols, column_mapping)
        if data_type == "site":
            return ImportService._validate_site(df, file_cols, column_mapping)

        raise ValueError(f"Unknown data_type: {data_type}")

    @staticmethod
    def _validate_aoi(df, file_cols, mapping: ColumnMapping) -> ValidationResult:
        errors = []
        scene_col = mapping.scene_col
        boundary_col = mapping.boundary_col

        if scene_col not in file_cols:
            errors.append(f"缺少场景列: '{scene_col}'")
        if boundary_col not in file_cols:
            errors.append(f"缺少边界列: '{boundary_col}'")

        if errors:
            return ValidationResult.failure(errors)

        # Validate WKT format for non-empty rows
        for idx, row in df.iterrows():
            wkt_str = str(row.get(boundary_col, "")).strip()
            wkt_str = wkt_str.strip('"').strip("'").strip()
            if not wkt_str or wkt_str.lower() == "nan":
                errors.append(f"第 {idx + 1} 行边界数据为空")
                continue
            try:
                wkt_loads(wkt_str)
            except Exception:
                errors.append(f"第 {idx + 1} 行 WKT 格式错误")

        preview_rows = df.head(5).to_dict(orient="records")
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success(preview_rows)

    @staticmethod
    def _validate_site(df, file_cols, mapping: ColumnMapping) -> ValidationResult:
        errors = []
        required = {
            "name_col": mapping.name_col,
            "lon_col": mapping.lon_col,
            "lat_col": mapping.lat_col,
            "freq_col": mapping.freq_col,
            "coverage_type_col": mapping.coverage_type_col,
        }

        for field_name, col_name in required.items():
            if col_name not in file_cols:
                errors.append(f"缺少字段映射: {field_name} -> '{col_name}'")

        if errors:
            return ValidationResult.failure(errors)

        # Validate coordinate types
        for idx, row in df.iterrows():
            lon_val = row.get(mapping.lon_col)
            lat_val = row.get(mapping.lat_col)
            try:
                float(lon_val)
            except (TypeError, ValueError):
                errors.append(f"第 {idx + 1} 行经度 '{lon_val}' 无法解析为数字")
            try:
                float(lat_val)
            except (TypeError, ValueError):
                errors.append(f"第 {idx + 1} 行纬度 '{lat_val}' 无法解析为数字")

        preview_rows = df.head(5).to_dict(orient="records")
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success(preview_rows)
