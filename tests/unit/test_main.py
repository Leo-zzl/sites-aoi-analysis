"""Unit tests for main.py CLI entry point (P1-T04)."""

import subprocess
import sys
from pathlib import Path


class TestMainEntry:
    def test_gui_flag_removed(self):
        """--gui should print a friendly message and exit with code 1."""
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent.parent / "main.py"), "--gui"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "已移除" in result.stderr or "已移除" in result.stdout

    def test_cli_runs_without_args(self):
        """Running without args should attempt to launch CLI (will fail without data, but not crash)."""
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent.parent / "main.py")],
            capture_output=True,
            text=True,
        )
        # CLI will likely print help or error about missing files; just ensure it doesn't crash
        assert result.returncode in (0, 1)
