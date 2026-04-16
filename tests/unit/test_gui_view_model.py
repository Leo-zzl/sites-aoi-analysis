"""Unit tests for GUI ViewModel logic."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from site_analysis.domain.value_objects import ColumnMapping


class TestGuiViewModel:
    """Test ViewModel state transitions and business logic."""

    @pytest.fixture
    def sample_aoi_file(self):
        df = pd.DataFrame({
            "场景": ["商业区"],
            "边界WKT": ["POLYGON((0 0,1 0,1 1,0 1,0 0))"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)
        yield tmp_path
        tmp_path.unlink()

    @pytest.fixture
    def sample_site_file(self):
        df = pd.DataFrame({
            "站点名": ["CELL_001"],
            "频段": ["2.6G"],
            "类型": ["室内"],
            "x": [113.5],
            "y": [22.5],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
            df.to_excel(tmp_path, index=False)
        yield tmp_path
        tmp_path.unlink()

    def test_load_aoi_file_reads_columns(self, sample_aoi_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_aoi_file(sample_aoi_file)
        assert vm.aoi_file_path == sample_aoi_file
        assert "场景" in vm.aoi_columns
        assert "边界WKT" in vm.aoi_columns

    def test_load_site_file_reads_columns_and_auto_detects_mapping(self, sample_site_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_site_file(sample_site_file)
        assert vm.site_file_path == sample_site_file
        assert "站点名" in vm.site_columns
        # Auto-detected mapping should pick up something (exact match depends on keywords)
        assert vm.site_mapping is not None

    def test_set_aoi_mapping(self, sample_aoi_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_aoi_file(sample_aoi_file)
        mapping = ColumnMapping(scene_col="场景", boundary_col="边界WKT")
        vm.set_aoi_mapping(mapping)
        assert vm.aoi_mapping.scene_col == "场景"
        assert vm.aoi_mapping.boundary_col == "边界WKT"

    def test_validate_success(self, sample_aoi_file, sample_site_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_aoi_file(sample_aoi_file)
        vm.load_site_file(sample_site_file)
        vm.set_aoi_mapping(ColumnMapping(scene_col="场景", boundary_col="边界WKT"))
        vm.set_site_mapping(ColumnMapping(
            name_col="站点名", lon_col="x", lat_col="y",
            freq_col="频段", coverage_type_col="类型"
        ))
        result = vm.validate()
        assert result.is_valid is True

    def test_validate_failure_missing_aoi_column(self, sample_aoi_file, sample_site_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_aoi_file(sample_aoi_file)
        vm.load_site_file(sample_site_file)
        vm.set_aoi_mapping(ColumnMapping(scene_col="场景", boundary_col="不存在的列"))
        vm.set_site_mapping(ColumnMapping(
            name_col="站点名", lon_col="x", lat_col="y",
            freq_col="频段", coverage_type_col="类型"
        ))
        result = vm.validate()
        assert result.is_valid is False

    def test_run_analysis_and_export(self, sample_aoi_file, sample_site_file):
        from site_analysis.interfaces.gui.view_model import MainViewModel

        vm = MainViewModel()
        vm.load_aoi_file(sample_aoi_file)
        vm.load_site_file(sample_site_file)
        vm.set_aoi_mapping(ColumnMapping(scene_col="场景", boundary_col="边界WKT"))
        vm.set_site_mapping(ColumnMapping(
            name_col="站点名", lon_col="x", lat_col="y",
            freq_col="频段", coverage_type_col="类型"
        ))
        vm.validate()
        vm.run_analysis()

        assert vm.analysis_result is not None
        assert len(vm.analysis_result.sites) == 1

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            out_path = Path(f.name)
        try:
            vm.export_results(out_path)
            assert out_path.exists()
            # Verify Summary sheet exists
            xls = pd.ExcelFile(out_path)
            assert "Summary" in xls.sheet_names
            assert "Results" in xls.sheet_names
        finally:
            out_path.unlink()
