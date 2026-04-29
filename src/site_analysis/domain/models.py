"""Domain entities: objects with identity and lifecycle."""

from dataclasses import dataclass, field
from typing import Optional

from site_analysis.domain.value_objects import AnalysisResult, CoverageType


@dataclass
class Site:
    """A cell site / base station."""

    name: str
    freq: str
    coverage_type: CoverageType
    lon: float
    lat: float
    extra_data: dict = field(default_factory=dict)
    result: AnalysisResult = field(default_factory=AnalysisResult)

    @property
    def is_indoor(self) -> bool:
        return self.coverage_type == CoverageType.INDOOR

    @property
    def is_outdoor(self) -> bool:
        return self.coverage_type == CoverageType.OUTDOOR


@dataclass
class AOI:
    """Area of Interest with a polygon boundary stored as WKT."""

    province: str
    city: str
    scene: str
    scene_big: str
    scene_small: str
    geometry: str  # WKT string; spatial calculations use GeometryAdapter
    extra_data: dict = field(default_factory=dict)
