"""Structural integration tests for the new MainWindow UI."""

import tkinter as tk
from tkinter import ttk

import pytest

from site_analysis.interfaces.gui.widgets.main_window import MainWindow
from site_analysis.interfaces.gui.widgets.preview_tree import PreviewTree
from site_analysis.interfaces.gui.widgets.mapping_frame import MappingFrame


class TestMainWindowStructure:
    """Verify the new MainWindow uses comboboxes instead of the old widgets."""

    @pytest.fixture
    def window(self):
        win = MainWindow()
        win.withdraw()
        yield win
        win.destroy()

    def _all_widgets(self, widget):
        for w in widget.winfo_children():
            yield w
            yield from self._all_widgets(w)

    def test_has_seven_comboboxes_for_column_mapping(self, window):
        combos = [w for w in self._all_widgets(window) if isinstance(w, ttk.Combobox)]
        assert len(combos) == 7, f"Expected 7 Comboboxes (AOI 2 + Site 5), found {len(combos)}"

    def test_has_aoi_file_button(self, window):
        assert window.aoi_btn is not None
        assert "选择" in window.aoi_btn.cget("text")

    def test_has_site_file_button(self, window):
        assert window.site_btn is not None
        assert "选择" in window.site_btn.cget("text")

    def test_has_validate_button(self, window):
        assert window.validate_btn is not None
        assert "校验" in window.validate_btn.cget("text")

    def test_has_browse_output_button(self, window):
        assert window.browse_btn is not None
        assert "浏览" in window.browse_btn.cget("text")

    def test_has_analyze_button(self, window):
        assert window.analyze_btn is not None
        assert window.analyze_btn.cget("text") == "开始分析"

    def test_no_old_preview_tree(self, window):
        previews = [w for w in self._all_widgets(window) if isinstance(w, PreviewTree)]
        assert len(previews) == 0, "New UI should not contain old PreviewTree"

    def test_no_old_mapping_frame(self, window):
        mappings = [w for w in self._all_widgets(window) if isinstance(w, MappingFrame)]
        assert len(mappings) == 0, "New UI should not contain old MappingFrame"

    def test_progress_canvas_exists(self, window):
        assert window.progress_canvas is not None
        assert isinstance(window.progress_canvas, tk.Canvas)

    def test_aoi_comboboxes_initialized_empty(self, window):
        assert window.aoi_scene_row.combo.get() == ""
        assert window.aoi_boundary_row.combo.get() == ""

    def test_site_comboboxes_initialized_empty(self, window):
        assert window.site_name_row.combo.get() == ""
        assert window.site_lon_row.combo.get() == ""
        assert window.site_lat_row.combo.get() == ""
        assert window.site_freq_row.combo.get() == ""
        assert window.site_cover_row.combo.get() == ""

    def test_analyze_button_disabled_by_default(self, window):
        assert str(window.analyze_btn.cget("state")) == "disabled"
