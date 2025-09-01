import pytest
from flask import Flask
from app.api.players import bp as players_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(players_bp)
    app.config['DATABASE'] = ':memory:'
    return app

@pytest.fixture
def client(app):
    return app.test_client()
