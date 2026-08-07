import pytest
from unittest.mock import patch
from flask import Flask

from app.api.admin import bp as admin_bp
from app.db import jobs


ADMIN_TOKEN = "test-admin-token"
AUTH_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["ADMIN_API_TOKEN"] = ADMIN_TOKEN
    app.register_blueprint(admin_bp)
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@patch("app.api.admin.service.init_database", return_value={"status": "ok"})
def test_init_db_success(mock_init_database, client):
    response = client.post("/api/admin/init-db", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    mock_init_database.assert_called_once()


@patch("app.api.admin.service.init_database", side_effect=RuntimeError("boom"))
def test_init_db_failure(mock_init_database, client):
    response = client.post("/api/admin/init-db", headers=AUTH_HEADERS)

    assert response.status_code == 500
    assert response.get_json() == {"error": "boom"}


@patch("app.api.admin.service.init_database")
def test_init_db_rejects_missing_token(mock_init_database, client):
    response = client.post("/api/admin/init-db")

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
    mock_init_database.assert_not_called()


@patch("app.api.admin.service.init_database")
def test_init_db_rejects_wrong_token(mock_init_database, client):
    response = client.post(
        "/api/admin/init-db", headers={"X-Admin-Token": "wrong"}
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
    mock_init_database.assert_not_called()


@patch("app.api.admin.jobs.start_update_job", return_value="job-123")
def test_update_db_starts_job(mock_start_update_job, client):
    response = client.post("/api/admin/update-db", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.get_json() == {"job_id": "job-123"}
    mock_start_update_job.assert_called_once()


@patch(
    "app.api.admin.jobs.start_update_job",
    side_effect=jobs.JobAlreadyRunningError("job-123"),
)
def test_update_db_rejects_concurrent_job(mock_start_update_job, client):
    response = client.post("/api/admin/update-db", headers=AUTH_HEADERS)

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "update already in progress",
        "job_id": "job-123",
    }


@patch("app.api.admin.jobs.start_update_job")
def test_update_db_rejects_missing_token(mock_start_update_job, client):
    response = client.post("/api/admin/update-db")

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
    mock_start_update_job.assert_not_called()


@patch(
    "app.api.admin.jobs.get_job",
    return_value={
        "job_id": "job-123",
        "status": "succeeded",
        "result": {"status": "ok", "heaps_processed": 1},
        "error": None,
        "started_at": "2026-08-06T00:00:00+00:00",
    },
)
def test_get_job_found(mock_get_job, client):
    response = client.get("/api/admin/jobs/job-123", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.get_json()["status"] == "succeeded"
    mock_get_job.assert_called_once_with("job-123")


@patch("app.api.admin.jobs.get_job", return_value=None)
def test_get_job_not_found(mock_get_job, client):
    response = client.get("/api/admin/jobs/does-not-exist", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.get_json() == {"error": "job not found"}


@patch("app.api.admin.jobs.get_job")
def test_get_job_rejects_missing_token(mock_get_job, client):
    response = client.get("/api/admin/jobs/job-123")

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
    mock_get_job.assert_not_called()


def test_init_db_rejects_get(client):
    response = client.get("/api/admin/init-db", headers=AUTH_HEADERS)
    assert response.status_code == 405


def test_update_db_rejects_get(client):
    response = client.get("/api/admin/update-db", headers=AUTH_HEADERS)
    assert response.status_code == 405
