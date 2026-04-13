"""Repository implementations for data access."""

from abc import ABC, abstractmethod
from typing import List

from site_analysis.domain.models import AOI, Site


class AoiRepository(ABC):
    """Abstract repository for AOI data."""

    @abstractmethod
    def load_all(self) -> List[AOI]:
        ...


class SiteRepository(ABC):
    """Abstract repository for site data."""

    @abstractmethod
    def load_all(self) -> List[Site]:
        ...
