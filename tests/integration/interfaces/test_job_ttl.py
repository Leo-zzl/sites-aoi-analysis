"""Unit tests for job/session TTL (P4-T03)."""

import time

from site_analysis.interfaces.api import _analysis_jobs, _schedule_job_cleanup


class TestJobTTL:
    def test_job_removed_after_ttl(self):
        """A completed job should be removed from memory after TTL expires."""
        job_id = "test_ttl_job"
        _analysis_jobs[job_id] = {
            "status": "success",
            "queue": None,
            "output_path": "/tmp/fake.xlsx",
            "summary": None,
            "error": None,
        }

        # Schedule cleanup with 0.1s delay for testing
        _schedule_job_cleanup(job_id, delay=0.1)
        assert job_id in _analysis_jobs

        time.sleep(0.3)
        assert job_id not in _analysis_jobs
