"""Release build integration tests — verify packaged backend is present and functional.

These tests are intended to run in CI *after* PyInstaller and electron-builder
have produced their artifacts, but *before* the release is published.
They guard against the class of bugs where the bundled Python backend is
missing from the final installer/portable package.

Run locally after building:
    pytest tests/integration/test_release_build.py -v -m release
"""

import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pytest

RELEASE_BACKEND_DIR = Path("dist-backend/site-analysis-api")
BACKEND_PORT = 8765
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/health"
STARTUP_TIMEOUT_SECONDS = 30


def _get_backend_exe_name() -> str:
    """Return the expected backend executable name for the current platform."""
    return "site-analysis-api.exe" if sys.platform == "win32" else "site-analysis-api"


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.mark.release
def test_pyinstaller_output_exists() -> None:
    """Verify PyInstaller output was copied to the expected dist-backend path."""
    assert RELEASE_BACKEND_DIR.exists(), (
        f"PyInstaller output directory not found at {RELEASE_BACKEND_DIR}. "
        "Did you forget to copy dist/site-analysis-api to dist-backend/site-analysis-api?"
    )

    exe_name = _get_backend_exe_name()
    exe_path = RELEASE_BACKEND_DIR / exe_name
    assert exe_path.exists(), (
        f"Backend executable not found: {exe_path}. "
        "The PyInstaller build may have failed or produced unexpected output."
    )

    # Ensure the directory is not empty (should contain bundled dependencies)
    files = list(RELEASE_BACKEND_DIR.iterdir())
    assert len(files) > 1, (
        f"Backend directory seems empty except for the exe: {files}. "
        "PyInstaller likely failed to collect dependencies."
    )


@pytest.mark.release
def test_bundled_backend_starts_and_responds() -> None:
    """Smoke-test the bundled backend by starting it and hitting /health."""
    exe_name = _get_backend_exe_name()
    exe_path = RELEASE_BACKEND_DIR / exe_name
    if not exe_path.exists():
        pytest.skip(f"Backend executable not found: {exe_path}")

    proc = None
    try:
        proc = subprocess.Popen(
            [str(exe_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the port to open, with a reasonable timeout
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if _is_port_open("127.0.0.1", BACKEND_PORT):
                break
            if proc.poll() is not None:
                stdout = proc.stdout.read().decode() if proc.stdout else ""
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                pytest.fail(
                    f"Backend process exited early with code {proc.returncode}.\n"
                    f"stdout:\n{stdout}\nstderr:\n{stderr}"
                )
            time.sleep(0.5)
        else:
            pytest.fail(
                f"Backend did not open port {BACKEND_PORT} within {STARTUP_TIMEOUT_SECONDS}s."
            )

        # Hit the health endpoint
        try:
            with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=5.0) as resp:
                data = resp.read().decode()
                assert '"status":"ok"' in data or '"status": "ok"' in data, (
                    f"Unexpected health response: {data}"
                )
        except Exception as exc:
            pytest.fail(f"Health check failed: {exc}")

    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


@pytest.mark.release
@pytest.mark.skipif(sys.platform != "win32", reason="Windows electron-builder artifact only")
def test_windows_artifact_contains_backend() -> None:
    """Verify the Windows zip artifact contains the bundled backend."""
    dist_dir = Path("dist")
    zip_files = list(dist_dir.glob("*-win.zip"))
    if not zip_files:
        pytest.skip("No Windows zip artifact found in dist/")

    exe_name = _get_backend_exe_name()
    backend_found = False
    for zf_path in zip_files:
        with zipfile.ZipFile(zf_path, "r") as zf:
            for name in zf.namelist():
                # electron-builder nests resources under <app-name>/resources/...
                if f"site-analysis-api/{exe_name}" in name.replace("\\", "/"):
                    backend_found = True
                    break
        if backend_found:
            break

    assert backend_found, (
        f"Backend executable ({exe_name}) not found inside any Windows zip artifact. "
        "electron-builder may have failed to include extraResources."
    )


@pytest.mark.release
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS electron-builder artifact only")
def test_macos_artifact_contains_backend() -> None:
    """Verify the macOS dmg/app contains the bundled backend."""
    dist_dir = Path("dist")
    app_bundles = list(dist_dir.glob("*.app"))
    if not app_bundles:
        pytest.skip("No macOS .app bundle found in dist/")

    exe_name = _get_backend_exe_name()
    backend_found = False
    for app in app_bundles:
        resources_dir = app / "Contents" / "Resources" / "site-analysis-api"
        if (resources_dir / exe_name).exists():
            backend_found = True
            break

    assert backend_found, (
        f"Backend executable ({exe_name}) not found in macOS app bundle. "
        "electron-builder may have failed to include extraResources."
    )
