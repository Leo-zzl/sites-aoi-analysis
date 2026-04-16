"""Integration tests for the analyze button thread coordination."""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from site_analysis.domain.value_objects import CoverageType
from site_analysis.interfaces.gui.widgets.main_window import MainWindow


class TestMainWindowAnalyzeFlow:
    """Test that clicking analyze runs the pipeline in a thread and reports results."""

    @pytest.fixture
    def window(self, tmp_path: Path):
        win = MainWindow()
        win.withdraw()

        # Mock repositories to avoid heavy spatial computation
        mock_aoi = MagicMock()
        mock_aoi.load_all.return_value = []

        mock_site = MagicMock()
        from site_analysis.domain.models import Site
        mock_site.load_all.return_value = [
            Site(name="s1", freq="2.1G", coverage_type=CoverageType.INDOOR, lon=113.0, lat=22.0),
            Site(name="s2", freq="2.6G", coverage_type=CoverageType.OUTDOOR, lon=113.1, lat=22.1),
        ]

        win.vm.aoi_repo = mock_aoi
        win.vm.site_repo = mock_site
        win.vm.aoi_file_path = tmp_path / "aoi.xlsx"
        win.vm.site_file_path = tmp_path / "site.xlsx"
        win.vm.aoi_file_path.write_text("dummy")
        win.vm.site_file_path.write_text("dummy")

        # Enable analyze button as if validation passed
        win.analyze_btn.config(state=tk.NORMAL)

        # Set a temp output path
        out = tmp_path / "result.xlsx"
        win.output_entry.delete(0, tk.END)
        win.output_entry.insert(0, str(out))

        yield win
        try:
            win.destroy()
        except tk.TclError:
            pass

    def test_analyze_thread_puts_success_in_queue(self, window):
        """Simulate worker logic in isolation to verify queue protocol."""
        q = queue.Queue()
        out_path = Path(window.output_entry.get())

        def worker():
            try:
                q.put(("stage", 10, "加载 AOI 数据...", ""))
                aois = window.vm.aoi_repo.load_all()
                q.put(("stage", 30, "加载站点数据...", f"AOI 数量: {len(aois)}"))
                sites = window.vm.site_repo.load_all()
                q.put(("stage", 50, "执行分析...", f"站点数量: {len(sites)}"))

                from site_analysis.application.analysis_service import SiteAnalysisService
                from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
                service = SiteAnalysisService(window.vm.aoi_repo, window.vm.site_repo, ExcelResultExporter())
                window.vm.analysis_result = service.run()

                q.put(("stage", 80, "导出结果文件...", ""))
                window.vm.export_results(out_path)
                q.put(("success", out_path))
            except Exception as exc:
                q.put(("error", str(exc)))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=10)

        assert not t.is_alive(), "Worker thread should finish within 10 seconds"

        items = []
        while not q.empty():
            items.append(q.get_nowait())

        types = [i[0] for i in items]
        assert "stage" in types
        assert "success" in types
        assert types[-1] == "success"

    def test_check_analysis_result_drains_queue_and_updates_ui(self, window):
        """Feed synthetic queue items and verify UI state changes."""
        from site_analysis.interfaces.gui.widgets.progress_dialog import ProgressDialog

        dialog = MagicMock()
        window._dialog = dialog

        window._result_queue.put(("stage", 10, "加载中...", ""))
        window._result_queue.put(("stage", 50, "分析中...", "1000 站点"))
        window._result_queue.put(("success", Path(window.output_entry.get())))

        # Set a mock analysis_result so the success path can read summary
        mock_result = MagicMock()
        from site_analysis.domain.value_objects import AnalysisSummary
        mock_result.summary = AnalysisSummary(total_sites=2, aoi_matched=1, indoor_sites=1, outdoor_sites=1, indoor_with_outdoor=1)
        window.vm.analysis_result = mock_result

        # Normally _check_analysis_result reschedules itself; we call it once manually
        # but because it may call self.after, we run it in a controlled loop
        for _ in range(20):
            window.update_idletasks()
            window._check_analysis_result(dialog)
            if dialog.close.called:
                break
            time.sleep(0.05)

        assert dialog.close.called
        assert window.analyze_btn.cget("text") == "开始分析"
        # Progress bar should be at 100%
        coords = window.progress_canvas.coords("all")
        assert coords  # canvas has drawn rectangles
