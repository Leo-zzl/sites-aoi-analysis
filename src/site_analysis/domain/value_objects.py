"""Domain value objects: immutable, identity-free business concepts."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional


_INDOOR_VALS = {"室内", "室分", "室分系统", "Indoor", "indoor"}
_OUTDOOR_VALS = {"室外", "宏站", "微站", "杆站", "Outdoor", "outdoor", "宏蜂窝", "微蜂窝"}


class CoverageType(Enum):
    """Classification of a site's coverage type."""

    INDOOR = auto()
    OUTDOOR = auto()
    UNKNOWN = auto()

    @classmethod
    def classify(cls, raw_value: Optional[str]) -> "CoverageType":
        val = str(raw_value).strip()
        if val in _INDOOR_VALS:
            return cls.INDOOR
        if val in _OUTDOOR_VALS:
            return cls.OUTDOOR
        return cls.UNKNOWN


@dataclass(frozen=True)
class UtmZone:
    """UTM projection zone represented as an EPSG code."""

    epsg: str

    @classmethod
    def from_lon_lat(cls, lon: float, lat: float) -> "UtmZone":
        zone = int((lon + 180) // 6) + 1
        epsg = f"EPSG:326{zone:02d}" if lat >= 0 else f"EPSG:327{zone:02d}"
        return cls(epsg)


@dataclass(frozen=True)
class AnalysisResult:
    """AOI matching + nearest outdoor station result for a single site."""

    aoi_province: str = ""
    aoi_city: str = ""
    aoi_scene: str = ""
    aoi_scene_big: str = ""
    aoi_scene_small: str = ""
    aoi_matched: bool = False

    nearest_outdoor_name: str = ""
    nearest_outdoor_freq: str = ""
    nearest_outdoor_distance_m: Optional[float] = None

    @property
    def aoi_match_status(self) -> str:
        return "已匹配" if self.aoi_matched else "未匹配"


class FileType(Enum):
    """Supported input file formats."""

    XLSX = auto()
    CSV = auto()

    @classmethod
    def from_path(cls, path: Path) -> "FileType":
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            return cls.XLSX
        if suffix == ".csv":
            return cls.CSV
        raise ValueError(f"Unsupported file format: {suffix}")


@dataclass(frozen=True)
class ColumnMapping:
    """User-selected column mapping from source file to domain fields."""

    name_col: str = ""
    lon_col: str = ""
    lat_col: str = ""
    freq_col: str = ""
    coverage_type_col: str = ""
    scene_col: str = ""
    boundary_col: str = ""

    def missing_aoi_fields(self) -> List[str]:
        """Return list of missing AOI field names."""
        missing = []
        if not self.scene_col:
            missing.append("scene_col")
        if not self.boundary_col:
            missing.append("boundary_col")
        return missing

    def missing_site_fields(self) -> List[str]:
        """Return list of missing Site field names."""
        missing = []
        if not self.name_col:
            missing.append("name_col")
        if not self.lon_col:
            missing.append("lon_col")
        if not self.lat_col:
            missing.append("lat_col")
        if not self.freq_col:
            missing.append("freq_col")
        if not self.coverage_type_col:
            missing.append("coverage_type_col")
        return missing

    def to_aoi_dict(self) -> Dict[str, str]:
        """Return mapping for AOI fields only."""
        return {
            "scene": self.scene_col,
            "boundary": self.boundary_col,
        }

    def to_site_dict(self) -> Dict[str, str]:
        """Return mapping for Site fields only."""
        return {
            "name": self.name_col,
            "lon": self.lon_col,
            "lat": self.lat_col,
            "freq": self.freq_col,
            "coverage_type": self.coverage_type_col,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a user-provided column mapping against source data."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    preview_rows: List[Dict] = field(default_factory=list)

    @classmethod
    def success(cls, preview_rows: Optional[List[Dict]] = None) -> "ValidationResult":
        return cls(is_valid=True, preview_rows=preview_rows or [])

    @classmethod
    def failure(cls, errors: List[str]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors)

    @classmethod
    def combine(cls, results: List["ValidationResult"]) -> "ValidationResult":
        is_valid = all(r.is_valid for r in results)
        errors = [err for r in results for err in r.errors]
        preview_rows = [row for r in results for row in r.preview_rows]
        return cls(is_valid=is_valid, errors=errors, preview_rows=preview_rows)


@dataclass(frozen=True)
class AnalysisSummary:
    """Summary statistics for a completed analysis run."""

    total_sites: int = 0
    aoi_matched: int = 0
    indoor_sites: int = 0
    outdoor_sites: int = 0
    indoor_with_outdoor: int = 0

    @classmethod
    def from_sites(cls, sites: List) -> "AnalysisSummary":
        # Delayed import to avoid circular dependency
        from site_analysis.domain.models import Site

        total = len(sites)
        aoi_matched = sum(1 for s in sites if s.result.aoi_matched)
        indoor = sum(1 for s in sites if s.coverage_type == CoverageType.INDOOR)
        outdoor = sum(1 for s in sites if s.coverage_type == CoverageType.OUTDOOR)
        indoor_with_outdoor = sum(
            1
            for s in sites
            if s.coverage_type == CoverageType.INDOOR
            and s.result.nearest_outdoor_distance_m is not None
        )
        return cls(
            total_sites=total,
            aoi_matched=aoi_matched,
            indoor_sites=indoor,
            outdoor_sites=outdoor,
            indoor_with_outdoor=indoor_with_outdoor,
        )
