"""Integration tests for cleanup, TTL, and upload limits (P4)."""

import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from site_analysis.interfaces.api import app, _upload_sessions, TEMP_DIR


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_aoi(tmp_path: Path):
    df = pd.DataFrame({
        "场景": ["scene1", "scene2"],
        "边界WKT": [
            "POLYGON ((113 22, 114 22, 114 23, 113 23, 113 22))",
            "POLYGON ((113 22, 114 22, 114 23, 113 23, 113 22))",
        ],
    })
    p = tmp_path / "aoi.xlsx"
    df.to_excel(p, index=False)
    return p


@pytest.fixture
def sample_site(tmp_path: Path):
    df = pd.DataFrame({
        "小区名称": ["s1", "s2"],
        "经度": [113.5, 113.6],
        "纬度": [22.5, 22.6],
        "使用频段": ["2.1G", "2.6G"],
        "覆盖类型": ["室内", "室外"],
    })
    p = tmp_path / "site.xlsx"
    df.to_excel(p, index=False)
    return p


class TestCleanup:
    @pytest.mark.slow
    def test_temp_files_removed_after_analysis(self, client, sample_aoi, sample_site, tmp_path: Path):
        """P4-T01: After analysis completes, temp upload files should be deleted."""
        with sample_aoi.open("rb") as f:
            aoi_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})
        with sample_site.open("rb") as f:
            site_res = client.post("/upload", data={"file_type": "site"}, files={"file": ("site.xlsx", f)})

        aoi_sid = aoi_res.json()["session_id"]
        site_sid = site_res.json()["session_id"]

        # Verify files exist before analysis
        aoi_path = Path(_upload_sessions[aoi_sid]["path"])
        site_path = Path(_upload_sessions[site_sid]["path"])
        assert aoi_path.exists()
        assert site_path.exists()

        out_path = str(tmp_path / "result.xlsx")
        res = client.post("/analyze", json={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
            "output_path": out_path,
            "scene_col": "场景",
            "boundary_col": "边界WKT",
            "name_col": "小区名称",
            "lon_col": "经度",
            "lat_col": "纬度",
            "freq_col": "使用频段",
            "coverage_type_col": "覆盖类型",
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Wait for background task to finish
        for _ in range(30):
            status = client.get(f"/jobs/{job_id}").json()
            if status["status"] in ("success", "error"):
                break
            time.sleep(0.2)

        assert status["status"] == "success"

        # Verify temp files are removed
        assert not aoi_path.exists()
        assert not site_path.exists()
        assert aoi_sid not in _upload_sessions
        assert site_sid not in _upload_sessions

    def test_cleanup_endpoint(self, client, sample_aoi):
        """P4-T02: POST /cleanup should clear TEMP_DIR."""
        with sample_aoi.open("rb") as f:
            upload_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})

        sid = upload_res.json()["session_id"]
        temp_path = Path(_upload_sessions[sid]["path"])
        assert temp_path.exists()

        res = client.post("/cleanup")
        assert res.status_code == 200
        assert not temp_path.exists()


class TestUploadLimit:
    def test_upload_oversized_file_rejected(self, client, tmp_path: Path):
        """P4-T04: Uploading a file >50MB should be rejected."""
        big_file = tmp_path / "big.xlsx"
        # Create a file slightly over 50MB
        big_file.write_bytes(b"x" * (50 * 1024 * 1024 + 1))

        with big_file.open("rb") as f:
            res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("big.xlsx", f)})

        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert "50MB" in data["error"]
