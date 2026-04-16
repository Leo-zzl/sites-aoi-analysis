"""Unit tests for MainWindow widget."""

import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from site_analysis.interfaces.gui.widgets.main_window import MainWindow


class TestMainWindow:
    """Test main GUI window behavior."""

    @pytest.fixture
    def window(self):
        win = MainWindow()
        win.update_idletasks()
        yield win
        win.destroy()

    def test_window_title(self, window):
        assert "小区-AOI空间匹配" in window.title()

    def test_analyze_button_disabled_initially(self, window):
        assert str(window.analyze_btn["state"]) == tk.DISABLED

    def test_aoi_path_shows_unselected_initially(self, window):
        assert window.aoi_path_label.cget("text") == "未选择"

    def test_site_path_shows_unselected_initially(self, window):
        assert window.site_path_label.cget("text") == "未选择"

    def test_output_entry_has_default_value(self, window):
        val = window.output_entry.get()
        assert "小区_AOI匹配" in val
        assert val.endswith(".xlsx")

    def test_validate_button_exists(self, window):
        assert window.validate_btn is not None
        assert "校验" in window.validate_btn.cget("text")

    def test_browse_output_button_exists(self, window):
        assert window.output_entry is not None

    def test_on_validate_shows_warning_when_no_files_selected(self, window):
        with patch("tkinter.messagebox.showwarning") as mock_warning:
            window._on_validate()
            mock_warning.assert_called_once()
            args = mock_warning.call_args[1]
            assert args.get("title") == "提示"
