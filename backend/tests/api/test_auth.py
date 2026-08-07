import pytest
from flask import Flask, jsonify

from app.api.auth import require_admin_token


@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/protected", methods=["GET"])
    @require_admin_token
    def protected():
        return jsonify({"ok": True})

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_missing_token_rejected(app, client):
    app.config["ADMIN_API_TOKEN"] = "secret"

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}


def test_wrong_token_rejected(app, client):
    app.config["ADMIN_API_TOKEN"] = "secret"

    response = client.get("/protected", headers={"X-Admin-Token": "wrong"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}


def test_correct_token_allowed(app, client):
    app.config["ADMIN_API_TOKEN"] = "secret"

    response = client.get("/protected", headers={"X-Admin-Token": "secret"})

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_unconfigured_token_always_rejected(app, client):
    app.config["ADMIN_API_TOKEN"] = None

    response = client.get("/protected", headers={"X-Admin-Token": ""})

    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
