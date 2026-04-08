from flask import Flask, jsonify

from adapters.flask_app.routes.books import books_bp
from adapters.flask_app.routes.loans import loans_bp
from adapters.flask_app.routes.members import members_bp
from adapters.flask_app.routes.reports import reports_bp
from backend.config.settings import ensure_data_files
from backend.services import LibraryService


def create_app() -> Flask:
    ensure_data_files()
    app = Flask(__name__)
    app.config["library_service"] = LibraryService()

    @app.get("/health")
    def health() -> tuple[dict, int]:
        return {"status": "ok"}, 200

    @app.errorhandler(Exception)
    def handle_error(exc: Exception):
        # Keep starter errors readable in API responses.
        return jsonify({"error": str(exc)}), 400

    app.register_blueprint(books_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(reports_bp)
    return app

