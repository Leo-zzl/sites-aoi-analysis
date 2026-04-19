"""Unit tests for FileType enumeration."""

from pathlib import Path

import pytest


class TestFileType:
    """Test file type detection."""

    def test_from_path_xlsx(self):
        from site_analysis.domain.value_objects import FileType

        assert FileType.from_path(Path("data.xlsx")) == FileType.XLSX
        assert FileType.from_path(Path("/tmp/DATA.XLSX")) == FileType.XLSX

    def test_from_path_csv(self):
        from site_analysis.domain.value_objects import FileType

        assert FileType.from_path(Path("data.csv")) == FileType.CSV
        assert FileType.from_path(Path("/tmp/DATA.CSV")) == FileType.CSV

    def test_from_path_unsupported(self):
        from site_analysis.domain.value_objects import FileType

        with pytest.raises(ValueError, match="Unsupported file format"):
            FileType.from_path(Path("data.txt"))
