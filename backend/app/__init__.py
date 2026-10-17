"""PlanIT Control REST API (Flask). Contract: docs/API.md."""
import logging

from flask import Flask, jsonify, request

from config import Config

from .extensions import cors, db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = False
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("pyfive", "apscheduler", "urllib3"):  # per-file / per-run chatter
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Folders for the SQLite database and uploaded photos.
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        from pathlib import Path
        Path(uri.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    # Only needed when the frontend runs on another origin (the Vite proxy and production are same-origin).
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}}, supports_credentials=True)

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify(message="Authentication required"), 401

    register_error_handlers(app)

    from .api import register_blueprints
    register_blueprints(app)

    from .cli import register_cli
    register_cli(app)

    with app.app_context():
        from .seed import init_db
        init_db(app)

    if app.config["ENABLE_JOBS"] and not app.config.get("TESTING"):
        from .jobs import start_jobs
        start_jobs(app)

    if app.config["APP_ENV"] == "production" and "SECRET_KEY" not in __import__("os").environ:
        app.logger.warning("SECRET_KEY is not set: sessions will reset on every restart")
    return app


def register_error_handlers(app):
    """JSON errors for API requests ({"message": ...}), matching the API contract."""
    def api_error(status, message):
        def handler(exc):
            if request.path.startswith("/api/"):
                return jsonify(message=message), status
            return exc
        return handler

    app.register_error_handler(404, api_error(404, "Not found"))
    app.register_error_handler(405, api_error(405, "Method not allowed"))
    app.register_error_handler(413, api_error(413, f"Upload too large (max {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)} MB)"))

    @app.errorhandler(500)
    def server_error(exc):
        if request.path.startswith("/api/"):
            return jsonify(message="Something went wrong on the server"), 500
        return exc
