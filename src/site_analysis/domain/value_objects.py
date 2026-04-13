"""Domain value objects: immutable, identity-free business concepts."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


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
