"""Integration test: Electron spawns Python backend and cleans it up on exit."""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ELECTRON_MAIN = REPO_ROOT / "electron" / "main.js"


def _is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_port_open(port):
            return True
        time.sleep(0.5)
    return False


def _wait_for_port_close(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _is_port_open(port):
            return True
        time.sleep(0.5)
    return False


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only local GUI test")
def test_electron_spawns_python_backend_and_cleans_up():
    """Verify Electron main.js starts the FastAPI backend and kills it on quit."""
    # Use npx electron for the test
    env = {
        **dict(subprocess.os.environ),
        "NODE_ENV": "test",
    }

    proc = subprocess.Popen(
        ["npx", "electron", "."],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        backend_ready = _wait_for_port(8765, timeout=25.0)
        assert backend_ready, "Python backend did not start within 25 seconds"

        # Sanity check: backend is actually serving API
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=5) as resp:
            assert resp.status == 200

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    backend_stopped = _wait_for_port_close(8765, timeout=10.0)
    assert backend_stopped, "Python backend was not cleaned up after Electron exited"
