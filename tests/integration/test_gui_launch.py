"""Integration test: verify main.py --gui actually loads the new MainWindow."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestGUILaunch:
    """Test that python3 main.py --gui uses the rewritten MainWindow."""

    def test_subprocess_main_py_loads_new_ui(self):
        script = Path(__file__).resolve().parents[2] / "verify_subprocess_ui.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "COMBOBOX_COUNT: 7" in result.stdout
        assert "NEW_UI: True" in result.stdout
