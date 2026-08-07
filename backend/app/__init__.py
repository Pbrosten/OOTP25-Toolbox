import os
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS


def create_app():
    # set production status
    is_production = False

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)
    if not is_production:
        app.config.from_object("config.DevConfig")
        print(app.config)
    else:
        app.config.from_object("config.ProdConfig")

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    )
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from app import db

    db.init_app(app)

    # Register API Blueprints
    from app.api import admin, players, projections, ratings

    app.register_blueprint(players.bp)
    app.register_blueprint(projections.bp)
    app.register_blueprint(ratings.bp)
    app.register_blueprint(admin.bp)

    return app
