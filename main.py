"""Compatibility entry point for the site analysis tool."""

import sys
from pathlib import Path

# Add src/ to Python path when running directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

from site_analysis.interfaces.cli import main

if __name__ == "__main__":
    main()
