#!/usr/bin/env python3
"""Entry point for PyInstaller-packaged backend."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "site_analysis.interfaces.api:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
    )
