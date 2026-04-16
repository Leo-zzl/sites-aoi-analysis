"""Tests for macOS tkinter grab/focus deadlock regression.

When ProgressDialog uses grab_set(), immediately calling messagebox on
macOS can deadlock the UI. These tests ensure the success path avoids
messagebox entirely and the error path defers it via after().
"""

import queue
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from site_analysis.domain.value_objects import AnalysisSummary
from site_analysis.interfaces.gui.widgets.main_window import MainWindow


class TestMacOSDeadlockRegression:
    """Prevent the 'stuck at 50%' ProgressDialog + messagebox deadlock."""

    @pytest.fixture
    def window(self, tmp_path: Path):
        win = MainWindow()
        win.withdraw()

        # Set up a minimal valid state
        win.vm.aoi_file_path = tmp_path / "aoi.xlsx"
        win.vm.site_file_path = tmp_path / "site.xlsx"
        win.vm.aoi_file_path.write_text("dummy")
        win.vm.site_file_path.write_text("dummy")
        win.vm.analysis_result = MagicMock()
        win.vm.analysis_result.summary = AnalysisSummary(
            total_sites=10,
            aoi_matched=5,
            indoor_sites=3,
            outdoor_sites=7,
            indoor_with_outdoor=2,
        )

        out = tmp_path / "result.xlsx"
        win.output_entry.delete(0, tk.END)
        win.output_entry.insert(0, str(out))

        yield win
        try:
            win.destroy()
        except tk.TclError:
            pass

    def test_success_path_does_not_call_messagebox_showinfo(self, window):
        """Success must not call messagebox.showinfo to avoid macOS deadlock."""
        dialog = MagicMock()
        window._result_queue.put(("stage", 50, "分析中...", ""))
        window._result_queue.put(("success", Path(window.output_entry.get())))

        with patch("tkinter.messagebox.showinfo") as mock_showinfo:
            # Drain queue directly
            for _ in range(5):
                window.update_idletasks()
                window._check_analysis_result(dialog)
                if dialog.close.called:
                    break

        assert dialog.close.called
        assert window.analyze_btn.cget("text") == "开始分析"
        mock_showinfo.assert_not_called()
        assert "分析完成" in window.result_label.cget("text")
        assert window.result_label.cget("fg") == "#16A34A"

    def test_error_path_defers_messagebox_via_after(self, window):
        """Error path must defer messagebox.showerror via after() on macOS."""
        dialog = MagicMock()
        window._result_queue.put(("error", "something went wrong"))

        original_after = window.after
        scheduled = []

        def capturing_after(ms, func=None, *args):
            if func is not None:
                scheduled.append((ms, func, args))
            return original_after(ms, func, *args)

        with patch.object(window, "after", side_effect=capturing_after):
            with patch("tkinter.messagebox.showerror") as mock_showerror:
                for _ in range(5):
                    window.update_idletasks()
                    window._check_analysis_result(dialog)
                    if dialog.close.called:
                        break

        assert dialog.close.called
        # showerror should NOT have been called synchronously
        mock_showerror.assert_not_called()
        # instead it should have been deferred via after()
        assert len(scheduled) >= 1
        # Find the lambda that wraps showerror
        assert any(
            callable(entry[1]) and entry[0] == 50
            for entry in scheduled
        )
