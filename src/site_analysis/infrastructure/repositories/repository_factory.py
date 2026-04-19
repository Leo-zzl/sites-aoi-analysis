"""Factory for creating the correct repository based on file format."""

from pathlib import Path
from typing import Optional

from site_analysis.domain.value_objects import ColumnMapping, FileType
from site_analysis.domain.repositories import AoiRepository, SiteRepository
from site_analysis.infrastructure.repositories.csv_aoi_repo import CsvAoiRepository
from site_analysis.infrastructure.repositories.csv_site_repo import CsvSiteRepository
from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository


class RepositoryFactory:
    """Create repository instances based on file extension."""

    @staticmethod
    def create_aoi_repo(file_path: Path, column_mapping: Optional[ColumnMapping] = None) -> AoiRepository:
        file_type = FileType.from_path(file_path)
        if file_type == FileType.XLSX:
            return ExcelAoiRepository(file_path, column_mapping=column_mapping)
        if file_type == FileType.CSV:
            return CsvAoiRepository(file_path, column_mapping=column_mapping)
        raise ValueError(f"Unsupported AOI repository format: {file_type}")

    @staticmethod
    def create_site_repo(file_path: Path, column_mapping: Optional[ColumnMapping] = None) -> SiteRepository:
        file_type = FileType.from_path(file_path)
        if file_type == FileType.XLSX:
            return ExcelSiteRepository(file_path, column_mapping=column_mapping)
        if file_type == FileType.CSV:
            return CsvSiteRepository(file_path, column_mapping=column_mapping)
        raise ValueError(f"Unsupported Site repository format: {file_type}")
