import logging
import threading
import uuid
from datetime import datetime, timezone

from flask import current_app

from app import LOG_FORMAT
from .service import update_database

# In-memory job registry. Does not survive a process restart and is not
# shared across multiple workers/replicas -- fine for the current
# single-process dev deployment, revisit if that ever changes.
_lock = threading.Lock()
_jobs = {}


class _JobLogHandler(logging.Handler):
    """Captures log records emitted by a single job's background thread
    into that job's registry entry, so GET /api/admin/jobs/{id} can return
    a log tail (e.g. update.py's "[27/76] Processing short heap: ..."
    lines). Installed on the root logger for the duration of the job --
    every pipeline logger (app.db.update, the Flask app logger used by
    service.py, etc.) propagates up to root, so one handler there catches
    all of it without threading a callback through update.py's internals.

    Filtered by thread id: other request threads keep logging concurrently
    while a job runs, and only one job's pipeline runs at a time (enforced
    by start_update_job()'s pending/running check), so thread id is enough
    to isolate this job's lines from everything else hitting the root
    logger.
    """

    def __init__(self, job_id, thread_ident):
        super().__init__(level=logging.INFO)
        self.setFormatter(logging.Formatter(LOG_FORMAT))
        self.job_id = job_id
        self.thread_ident = thread_ident

    def emit(self, record):
        if record.thread != self.thread_ident:
            return
        job = _jobs.get(self.job_id)
        if job is not None:
            job["logs"].append(self.format(record))


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
            "logs": [],
        }

    thread = threading.Thread(target=_run_update_job, args=(app, job_id), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _run_update_job(app, job_id):
    with app.app_context():
        _jobs[job_id]["status"] = "running"
        handler = _JobLogHandler(job_id, threading.get_ident())
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            result = update_database()
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
        else:
            _jobs[job_id]["status"] = "succeeded"
            _jobs[job_id]["result"] = result
        finally:
            root_logger.removeHandler(handler)
