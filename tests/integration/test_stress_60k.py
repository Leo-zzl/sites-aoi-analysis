"""Stress test with 600K+ site rows against 100 AOI polygons.

Requires pre-generated fixtures:
    tests/fixtures/stress_aoi.xlsx
    tests/fixtures/stress_site.xlsx

Generate them with:
    PYTHONPATH=src python scripts/generate_stress_data.py
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from site_analysis.interfaces.api import app

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
AOI_PATH = FIXTURES_DIR / "stress_aoi.xlsx"
SITE_PATH = FIXTURES_DIR / "stress_site.xlsx"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.skipif(not AOI_PATH.exists() or not SITE_PATH.exists(), reason="Stress fixtures not generated")
@pytest.mark.slow
class TestStress600K:
    def test_upload_stress_files(self, client):
        with AOI_PATH.open("rb") as f:
            aoi_res = client.post("/upload", data={"file_type": "aoi"}, files={"file": ("stress_aoi.xlsx", f)})
        assert aoi_res.status_code == 200
        assert "session_id" in aoi_res.json()

        with SITE_PATH.open("rb") as f:
            site_res = client.post("/upload", data={"file_type": "site"}, files={"file": ("stress_site.xlsx", f)})
        assert site_res.status_code == 200
        assert "session_id" in site_res.json()

        return aoi_res.json()["session_id"], site_res.json()["session_id"]

    def test_validate_stress_files(self, client):
        aoi_sid, site_sid = self.test_upload_stress_files(client)

        res = client.post("/validate", json={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
            "scene_col": "场景",
            "boundary_col": "物业边界",
            "name_col": "小区名称",
            "lon_col": "经度",
            "lat_col": "纬度",
            "freq_col": "使用频段",
            "coverage_type_col": "覆盖类型",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True, f"Validation errors: {data.get('errors')}"

    def test_analyze_stress_files(self, client, tmp_path: Path):
        aoi_sid, site_sid = self.test_upload_stress_files(client)

        out_path = str(tmp_path / "stress_result.xlsx")
        res = client.post("/analyze", json={
            "aoi_session_id": aoi_sid,
            "site_session_id": site_sid,
            "output_path": out_path,
            "scene_col": "场景",
            "boundary_col": "物业边界",
            "name_col": "小区名称",
            "lon_col": "经度",
            "lat_col": "纬度",
            "freq_col": "使用频段",
            "coverage_type_col": "覆盖类型",
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Stream progress
        start = time.time()
        with client.stream("GET", f"/progress/{job_id}") as stream:
            for line in stream.iter_lines():
                if "complete" in line:
                    break

        elapsed = time.time() - start

        # Verify completion
        for _ in range(60):
            status = client.get(f"/jobs/{job_id}").json()
            if status["status"] in ("success", "error"):
                break
            time.sleep(0.5)

        assert status["status"] == "success", f"Analysis failed: {status.get('error')}"
        assert Path(out_path).exists()

        summary = status["summary"]
        assert summary["total_sites"] == 600_000
        print(f"\n  Stress test completed in {elapsed:.1f}s")
        print(f"    Total sites : {summary['total_sites']:,}")
        print(f"    AOI matched : {summary['aoi_matched']:,}")
        print(f"    Indoor      : {summary['indoor_sites']:,}")
        print(f"    Outdoor     : {summary['outdoor_sites']:,}")
        print(f"    Indoor+outdoor nearby: {summary['indoor_with_outdoor']:,}")
