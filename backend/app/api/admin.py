from flask import Blueprint, jsonify

from app.api.auth import require_admin_token
from app.db import jobs, service
from app.db.connection import get_db, close_db

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.route("/init-db", methods=["POST"])
@require_admin_token
def init_db():
    """
    Initialize the database schema.

    Returns:
        JSON response:
            - The service result summary on success.
            - 500 error on failure.
    """
    try:
        result = service.init_database()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/update-db", methods=["POST"])
@require_admin_token
def update_db():
    """
    Start ingesting any new dump heaps and running the migration/projection
    pipeline as a background job.

    Returns:
        JSON response:
            - 202 with {"job_id": ...} once the job is started.
            - 409 with {"error": ..., "job_id": ...} if a job is already
              pending/running.
    """
    try:
        job_id = jobs.start_update_job()
    except jobs.JobAlreadyRunningError as e:
        return jsonify({"error": str(e), "job_id": e.job_id}), 409
    return jsonify({"job_id": job_id}), 202


@bp.route("/jobs/<job_id>", methods=["GET"])
@require_admin_token
def get_job(job_id):
    """
    Retrieve the status of an update-db job.

    Returns:
        JSON response:
            - The job's current status/result/error/logs.
            - 404 if no job exists with that id.
    """
    job = jobs.get_job(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@bp.route("/league-baselines", methods=["GET"])
@require_admin_token
def get_league_baselines():
    """
    Retrieve recent history of this save's recalibrated run-value
    constants (ticket 0066) -- one row per long/yearly heap that has
    computed them, most recent first.

    Returns:
        JSON response: a list of {id, computed_at, window_start_year,
        window_end_year, lg_woba, lg_pwoba, ra9_baseline,
        batting_pa_sample, pitching_bf_sample}, newest first.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, computed_at, window_start_year, window_end_year, "
                "lg_woba, lg_pwoba, ra9_baseline, batting_pa_sample, "
                "pitching_bf_sample "
                "FROM league_baselines ORDER BY id DESC LIMIT 10"
            )
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        close_db()


@bp.route("/market-baselines", methods=["GET"])
@require_admin_token
def get_market_baselines():
    """
    Retrieve recent history of this save's recalibrated contract_value.py
    constants (ticket 0066) -- one row per long/yearly heap that has
    computed them, most recent first.

    Returns:
        JSON response: a list of {id, computed_at, war_dollar_value,
        war_dollar_value_sample, recommendation_extend_threshold,
        threshold_cohort_sample}, newest first.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, computed_at, war_dollar_value, "
                "war_dollar_value_sample, recommendation_extend_threshold, "
                "threshold_cohort_sample "
                "FROM market_baselines ORDER BY id DESC LIMIT 10"
            )
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        close_db()
