"""ViewModel that binds GUI state to domain/application services."""

from pathlib import Path
from typing import List, Optional

from site_analysis.application.analysis_service import AnalysisResultContainer, SiteAnalysisService
from site_analysis.application.import_service import ImportService
from site_analysis.domain.value_objects import (
    ColumnMapping,
    ValidationResult,
)
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory


# Keyword sets for auto-detection
_NAME_KEYWORDS = {"小区名称", "站点名", "name", "站点名称", "小区"}
_LON_KEYWORDS = {"经度", "lon", "longitude", "x", "lng"}
_LAT_KEYWORDS = {"纬度", "lat", "latitude", "y"}
_FREQ_KEYWORDS = {"使用频段", "频段", "freq", "frequency"}
_COVERAGE_KEYWORDS = {"覆盖类型", "类型", "cover", "coverage", "covertype"}
_SCENE_KEYWORDS = {"场景", "scene", "场景名", "场景名称"}
_BOUNDARY_KEYWORDS = {"边界", "boundary", "wkt", "边界WKT", "物业边界", "polygon"}


def _detect_column(columns: List[str], keywords: set) -> str:
    """Return the first column that matches any keyword (case-insensitive)."""
    for c in columns:
        col_clean = str(c).strip().lower().replace(" ", "").replace("_", "")
        if col_clean in keywords or any(k in col_clean for k in keywords):
            return c
    return ""


class MainViewModel:
    """State manager for the GUI."""

    def __init__(self):
        self.aoi_file_path: Optional[Path] = None
        self.site_file_path: Optional[Path] = None

        self.aoi_columns: List[str] = []
        self.site_columns: List[str] = []

        self.aoi_mapping: ColumnMapping = ColumnMapping()
        self.site_mapping: ColumnMapping = ColumnMapping()

        self.validation_result: Optional[ValidationResult] = None
        self.analysis_result: Optional[AnalysisResultContainer] = None

        self.aoi_repo = None
        self.site_repo = None

        self._import_service = ImportService()
        self._repository_factory = RepositoryFactory()

    def load_aoi_file(self, path: Path) -> None:
        self.aoi_file_path = path
        self.aoi_columns = self._import_service.preview_columns(path)
        scene_col = _detect_column(self.aoi_columns, _SCENE_KEYWORDS)
        boundary_col = _detect_column(self.aoi_columns, _BOUNDARY_KEYWORDS)
        self.aoi_mapping = ColumnMapping(scene_col=scene_col, boundary_col=boundary_col)

    def load_site_file(self, path: Path) -> None:
        self.site_file_path = path
        self.site_columns = self._import_service.preview_columns(path)
        name_col = _detect_column(self.site_columns, _NAME_KEYWORDS)
        lon_col = _detect_column(self.site_columns, _LON_KEYWORDS)
        lat_col = _detect_column(self.site_columns, _LAT_KEYWORDS)
        freq_col = _detect_column(self.site_columns, _FREQ_KEYWORDS)
        coverage_type_col = _detect_column(self.site_columns, _COVERAGE_KEYWORDS)
        self.site_mapping = ColumnMapping(
            name_col=name_col,
            lon_col=lon_col,
            lat_col=lat_col,
            freq_col=freq_col,
            coverage_type_col=coverage_type_col,
        )

    def set_aoi_mapping(self, mapping: ColumnMapping) -> None:
        self.aoi_mapping = mapping

    def set_site_mapping(self, mapping: ColumnMapping) -> None:
        self.site_mapping = mapping

    def validate(self) -> ValidationResult:
        """Validate both AOI and Site mappings."""
        results = []

        if self.aoi_file_path:
            results.append(
                self._import_service.validate_mapping(
                    self.aoi_file_path, self.aoi_mapping, "aoi"
                )
            )

        if self.site_file_path:
            results.append(
                self._import_service.validate_mapping(
                    self.site_file_path, self.site_mapping, "site"
                )
            )

        self.validation_result = ValidationResult.combine(results)
        return self.validation_result

    def run_analysis(self) -> AnalysisResultContainer:
        """Run the full spatial analysis pipeline."""
        if not self.aoi_file_path or not self.site_file_path:
            raise ValueError("AOI 文件和站点文件都必须先选择")

        self.aoi_repo = self._repository_factory.create_aoi_repo(
            self.aoi_file_path, self.aoi_mapping
        )
        self.site_repo = self._repository_factory.create_site_repo(
            self.site_file_path, self.site_mapping
        )
        exporter = ExcelResultExporter()
        service = SiteAnalysisService(self.aoi_repo, self.site_repo, exporter)
        self.analysis_result = service.run()
        return self.analysis_result

    def export_results(self, output_path: Path) -> None:
        """Export analysis results with summary sheet."""
        if self.analysis_result is None:
            raise ValueError("请先运行分析")
        exporter = ExcelResultExporter()
        exporter.export_with_summary(
            self.analysis_result.sites,
            self.analysis_result.summary,
            output_path,
        )
