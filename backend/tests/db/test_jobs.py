import threading
import time
from unittest.mock import patch

import pytest

from app.db import jobs


@pytest.fixture(autouse=True)
def clear_jobs():
    jobs._jobs.clear()
    yield
    jobs._jobs.clear()


def wait_for_status(job_id, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = jobs.get_job(job_id)
        if job["status"] not in ("pending", "running"):
            return job
        time.sleep(0.01)
    raise TimeoutError(f"job {job_id} did not finish in time")


@patch(
    "app.db.jobs.update_database",
    return_value={"status": "ok", "heaps_processed": 1},
)
def test_start_update_job_succeeds(mock_update_database, app):
    job_id = jobs.start_update_job()
    job = wait_for_status(job_id)

    assert job["status"] == "succeeded"
    assert job["result"] == {"status": "ok", "heaps_processed": 1}
    assert job["error"] is None
    mock_update_database.assert_called_once()


@patch("app.db.jobs.update_database", side_effect=RuntimeError("boom"))
def test_start_update_job_records_failure(mock_update_database, app):
    job_id = jobs.start_update_job()
    job = wait_for_status(job_id)

    assert job["status"] == "failed"
    assert job["error"] == "boom"
    assert job["result"] is None


def test_start_update_job_rejects_concurrent_run(app):
    started = threading.Event()
    release = threading.Event()

    def blocking_update():
        started.set()
        release.wait(timeout=2)
        return {"status": "ok"}

    with patch("app.db.jobs.update_database", side_effect=blocking_update):
        job_id = jobs.start_update_job()
        assert started.wait(timeout=2)

        with pytest.raises(jobs.JobAlreadyRunningError) as exc_info:
            jobs.start_update_job()
        assert exc_info.value.job_id == job_id

        release.set()
        wait_for_status(job_id)


def test_get_job_unknown_returns_none(app):
    assert jobs.get_job("does-not-exist") is None
