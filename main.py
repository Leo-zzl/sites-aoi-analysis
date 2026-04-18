"""Compatibility entry point for the site analysis tool."""

import sys
from pathlib import Path

# Add src/ to Python path when running directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        print("--gui 参数已移除，请使用 npm start 启动桌面应用")
        sys.exit(1)
    from site_analysis.interfaces.cli import main
    main()
