"""Compatibility entry point for the site analysis tool."""

import sys
from pathlib import Path

# Add src/ to Python path when running directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        from site_analysis.interfaces.gui.app import run_gui
        run_gui()
    else:
        from site_analysis.interfaces.cli import main
        main()
