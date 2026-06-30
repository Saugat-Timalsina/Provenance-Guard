"""
app.py

Application factory for Provenance Guard.

The factory pattern keeps the app testable and the import graph clean:
  - No circular imports (blueprints import 'extensions', not 'app')
  - Tests can call create_app() with a custom config in isolation
  - All extensions are initialised in one controlled place

Milestone 5 additions:
  - Flask-Limiter initialised via extensions.limiter.init_app(app)
  - Limiter is already imported by routes/submit.py from extensions.py
"""

import os

from flask import Flask, jsonify

from config.settings import config_map
from database.db import close_db, init_db
from extensions import limiter
from routes.appeal import appeal_bp
from routes.log import log_bp
from routes.submit import submit_bp


def create_app() -> Flask:
    """
    Create, configure, and return the Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=False)

    # --- Configuration ---
    env          = os.environ.get("FLASK_ENV", "development")
    config_class = config_map.get(env, config_map["development"])
    app.config.from_object(config_class)

    # --- Extensions ---
    # limiter is created in extensions.py with no app attached.
    # init_app() wires it to this specific app instance.
    limiter.init_app(app)

    # --- Database ---
    app.teardown_appcontext(close_db)
    init_db(app)

    # --- Health check ---
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "provenance-guard"}), 200

    # --- Blueprints ---
    app.register_blueprint(submit_bp)
    app.register_blueprint(appeal_bp)
    app.register_blueprint(log_bp)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=flask_app.config.get("DEBUG", False),
    )
