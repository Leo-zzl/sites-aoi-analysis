"""Functional tests for file selection and combobox population in MainWindow."""

import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from site_analysis.interfaces.gui.widgets.main_window import MainWindow


class TestMainWindowFileSelection:
    """Test that selecting files populates column mapping comboboxes."""

    @pytest.fixture
    def window(self):
        win = MainWindow()
        win.withdraw()
        yield win
        win.destroy()

    @pytest.fixture
    def sample_aoi_path(self, tmp_path: Path):
        p = tmp_path / "aoi.xlsx"
        df = pd.DataFrame({
            "场景名称": ["商业区"],
            "边界WKT": ["POLYGON((0 0,1 0,1 1,0 1,0 0))"],
        })
        df.to_excel(p, index=False)
        return str(p)

    @pytest.fixture
    def sample_site_path(self, tmp_path: Path):
        p = tmp_path / "site.xlsx"
        df = pd.DataFrame({
            "站点名": ["CELL_001"],
            "频段": ["2.6G"],
            "覆盖类型": ["室内"],
            "经度": [113.5],
            "纬度": [22.5],
        })
        df.to_excel(p, index=False)
        return str(p)

    def test_select_aoi_file_populates_comboboxes(self, window, sample_aoi_path):
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_aoi_path):
            window._on_select_aoi()

        assert window.aoi_path_label.cget("text") == "aoi.xlsx"
        assert "场景名称" in window.aoi_scene_row.combo["values"]
        assert "边界WKT" in window.aoi_boundary_row.combo["values"]
        # Auto-detection should pick matching columns
        assert window.aoi_scene_row.combo.get() == "场景名称"
        assert window.aoi_boundary_row.combo.get() == "边界WKT"

    def test_select_site_file_populates_comboboxes(self, window, sample_site_path):
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_site_path):
            window._on_select_site()

        assert window.site_path_label.cget("text") == "site.xlsx"
        assert "站点名" in window.site_name_row.combo["values"]
        assert "经度" in window.site_lon_row.combo["values"]
        assert "纬度" in window.site_lat_row.combo["values"]
        assert "频段" in window.site_freq_row.combo["values"]
        assert "覆盖类型" in window.site_cover_row.combo["values"]
        # Auto-detection should pick matching columns
        assert window.site_name_row.combo.get() == "站点名"
        assert window.site_lon_row.combo.get() == "经度"
        assert window.site_lat_row.combo.get() == "纬度"
        assert window.site_freq_row.combo.get() == "频段"
        assert window.site_cover_row.combo.get() == "覆盖类型"

    def test_select_aoi_then_site_enables_validation(self, window, sample_aoi_path, sample_site_path):
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_aoi_path):
            window._on_select_aoi()
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_site_path):
            window._on_select_site()

        # After both files selected, analyze should still be disabled until validation
        assert str(window.analyze_btn.cget("state")) == "disabled"

    def test_validate_with_both_files_enables_analyze(self, window, sample_aoi_path, sample_site_path):
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_aoi_path):
            window._on_select_aoi()
        with patch("tkinter.filedialog.askopenfilename", return_value=sample_site_path):
            window._on_select_site()

        with patch("tkinter.messagebox.showwarning") as mock_warn, \
             patch("tkinter.messagebox.showerror") as mock_err:
            window._on_validate()
            mock_warn.assert_not_called()
            mock_err.assert_not_called()

        assert str(window.analyze_btn.cget("state")) == "normal"
        assert "校验通过" in window.result_label.cget("text")
