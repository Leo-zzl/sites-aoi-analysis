"""Unit tests for the FastAPI backend."""

import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from site_analysis.interfaces.api import app


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


class TestHealth:
    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestUpload:
    def test_upload_aoi(self, client, sample_aoi):
        with sample_aoi.open("rb") as f:
            res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert "场景" in data["columns"]
        assert "边界WKT" in data["columns"]

    def test_upload_site(self, client, sample_site):
        with sample_site.open("rb") as f:
            res = client.post("/upload", data={"file_type": "site"}, files={"file": ("site.xlsx", f)})
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert data["mapping"]["name_col"] == "小区名称"


class TestValidate:
    def test_validate_success(self, client, sample_aoi, sample_site):
        with sample_aoi.open("rb") as f:
            aoi_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})
        with sample_site.open("rb") as f:
            site_res = client.post("/upload", data={"file_type": "site"}, files={"file": ("site.xlsx", f)})

        aoi_sid = aoi_res.json()["session_id"]
        site_sid = site_res.json()["session_id"]

        res = client.post("/validate", data={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
            "scene_col": "场景",
            "boundary_col": "边界WKT",
            "name_col": "小区名称",
            "lon_col": "经度",
            "lat_col": "纬度",
            "freq_col": "使用频段",
            "coverage_type_col": "覆盖类型",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_failure_missing_mapping(self, client, sample_aoi, sample_site):
        with sample_aoi.open("rb") as f:
            aoi_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})
        with sample_site.open("rb") as f:
            site_res = client.post("/upload", data={"file_type": "site"}, files={"file": ("site.xlsx", f)})

        aoi_sid = aoi_res.json()["session_id"]
        site_sid = site_res.json()["session_id"]

        res = client.post("/validate", data={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
            "scene_col": "场景",
            "boundary_col": "",  # missing
            "name_col": "小区名称",
            "lon_col": "经度",
            "lat_col": "纬度",
            "freq_col": "使用频段",
            "coverage_type_col": "覆盖类型",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert any("边界" in e for e in data["errors"])


class TestAnalyze:
    @pytest.mark.slow
    def test_analyze_and_progress(self, client, sample_aoi, sample_site):
        with sample_aoi.open("rb") as f:
            aoi_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("aoi.xlsx", f)})
        with sample_site.open("rb") as f:
            site_res = client.post("/upload", data={"file_type": "site"}, files={"file": ("site.xlsx", f)})

        aoi_sid = aoi_res.json()["session_id"]
        site_sid = site_res.json()["session_id"]

        res = client.post("/analyze", data={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
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
        assert job_id

        # Poll SSE briefly to confirm progress stream starts
        with client.stream("GET", f"/progress/{job_id}") as stream:
            chunks = []
            for line in stream.iter_lines():
                chunks.append(line)
                if "complete" in line or len(chunks) > 20:
                    break

        # Wait for background task to finish
        for _ in range(30):
            status = client.get(f"/jobs/{job_id}").json()
            if status["status"] in ("success", "error"):
                break
            time.sleep(0.2)

        assert status["status"] == "success"
        assert status["summary"]["total_sites"] == 2

        dl = client.get(f"/download/{job_id}")
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
