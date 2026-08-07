import threading
import uuid
from datetime import datetime, timezone

from flask import current_app

from .service import update_database

# In-memory job registry. Does not survive a process restart and is not
# shared across multiple workers/replicas -- fine for the current
# single-process dev deployment, revisit if that ever changes.
_lock = threading.Lock()
_jobs = {}


class JobAlreadyRunningError(Exception):
    """Raised when a new update-db job is requested while one is already
    pending/running."""

    def __init__(self, job_id):
        self.job_id = job_id
        super().__init__("update already in progress")


def start_update_job() -> str:
    """Start update_database() on a background thread.

    Raises JobAlreadyRunningError if a job started through this registry is
    already pending/running -- lets the API return a synchronous 409 with
    the running job's id for the common case. This does not cover an
    in-flight CLI run (the CLI bypasses this registry entirely): that's
    guarded by service.update_database()'s own lock, which raises
    UpdateAlreadyRunningError inside the background thread and is reported
    as this job's failure, same as any other exception from the run.

    Returns the new job's id.
    """
    app = current_app._get_current_object()

    with _lock:
        for job in _jobs.values():
            if job["status"] in ("pending", "running"):
                raise JobAlreadyRunningError(job["job_id"])

        job_id = str(uuid.uuid4())
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "result": None,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    thread = threading.Thread(target=_run_update_job, args=(app, job_id), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _run_update_job(app, job_id):
    with app.app_context():
        _jobs[job_id]["status"] = "running"
        try:
            result = update_database()
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
        else:
            _jobs[job_id]["status"] = "succeeded"
            _jobs[job_id]["result"] = result
