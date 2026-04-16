"""Unit tests for RepositoryFactory."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from site_analysis.domain.value_objects import ColumnMapping


class TestRepositoryFactory:
    """Test factory creates correct repository types."""

    def test_create_aoi_xlsx(self):
        from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory
        from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository

        df = pd.DataFrame({"a": [1]})
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            mapping = ColumnMapping(scene_col="a", boundary_col="a")
            repo = RepositoryFactory.create_aoi_repo(tmp_path, mapping)
            assert isinstance(repo, ExcelAoiRepository)
        finally:
            tmp_path.unlink()

    def test_create_aoi_csv(self):
        from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory
        from site_analysis.infrastructure.repositories.csv_aoi_repo import CsvAoiRepository

        tmp_path = Path(tempfile.mktemp(suffix=".csv"))
        tmp_path.write_text("a,b\n1,2\n", encoding="utf-8")

        try:
            mapping = ColumnMapping(scene_col="a", boundary_col="b")
            repo = RepositoryFactory.create_aoi_repo(tmp_path, mapping)
            assert isinstance(repo, CsvAoiRepository)
        finally:
            tmp_path.unlink()

    def test_create_site_xlsx(self):
        from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory
        from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository

        df = pd.DataFrame({"a": [1]})
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)

        try:
            mapping = ColumnMapping(name_col="a")
            repo = RepositoryFactory.create_site_repo(tmp_path, mapping)
            assert isinstance(repo, ExcelSiteRepository)
        finally:
            tmp_path.unlink()

    def test_create_site_csv(self):
        from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory
        from site_analysis.infrastructure.repositories.csv_site_repo import CsvSiteRepository

        tmp_path = Path(tempfile.mktemp(suffix=".csv"))
        tmp_path.write_text("a,b\n1,2\n", encoding="utf-8")

        try:
            mapping = ColumnMapping(name_col="a")
            repo = RepositoryFactory.create_site_repo(tmp_path, mapping)
            assert isinstance(repo, CsvSiteRepository)
        finally:
            tmp_path.unlink()

    def test_unsupported_format(self):
        from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory

        tmp_path = Path("data.txt")
        mapping = ColumnMapping()
        with pytest.raises(ValueError, match="Unsupported file format"):
            RepositoryFactory.create_aoi_repo(tmp_path, mapping)
