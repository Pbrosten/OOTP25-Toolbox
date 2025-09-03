import pytest
from flask import Flask
from app.api.players import bp as players_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(players_bp)
    app.config['DATABASE'] = ':memory:'
    app.config['STAGGING'] = ':memory'
    app.config['DUMP_PATH'] = "/fake/dump/path"
    with app.app_context():
        yield app 
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_ratings_data():
    return {
        "player_id": "test_player",
        "rating_id": "R001",
        "rating_date": "2025-09-01",
        "birth_date": "2000-01-01",
        "position": "SS",
        "bats": "R",
        "prone_overall": 50,  # Should classify as 'Normal'
        "babip": 50,
        "gap": 50,
        "eye": 50,
        "power": 50,
        "strikeouts": 50,
        "speed": 50,
        "steal": 50,
        "baserunning": 50,
        "pos2": 50,
        "pos3": 50,
        "pos4": 50,
        "pos5": 50,
        "pos6": 50,
        "pos7": 50,
        "pos8": 50,
        "pos9": 50
    }