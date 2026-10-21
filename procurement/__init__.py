"""Application composition. Business operations live outside the HTTP boundary."""

from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import Flask, request, session
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import OperationalError

from . import db
from .errors import DomainError


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get(
            "DATABASE_URL", f"sqlite:///{Path(app.instance_path) / 'procurement.sqlite'}"
        ),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / "documents"),
        AI_API_KEY=os.environ.get("GEMINI_API_KEY", ""),
        AI_MODEL=os.environ.get("AI_MODEL", ""),
        DEPLOYMENT=os.environ.get("DEPLOYMENT") == "1",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        if app.config["DEPLOYMENT"]:
            raise RuntimeError("SECRET_KEY must be configured for deployment.")
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        key_file = Path(app.instance_path) / "secret.key"
        if not key_file.exists():
            key_file.write_text(secrets.token_hex(32), encoding="utf-8")
        app.config["SECRET_KEY"] = key_file.read_text(encoding="utf-8").strip()
    if len(app.config["SECRET_KEY"]) < 16:
        raise RuntimeError("SECRET_KEY must contain at least 16 characters.")
    db.init_app(app)
    from .auth import bp as auth_bp
    from .auth import load_user
    from .documents import bp as documents_bp
    from .presentation import render_page
    from .web import bp as web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(documents_bp)
    app.before_request(load_user)

    @app.before_request
    def check_csrf() -> None:
        if request.method == "POST":
            token = request.form.get("csrf_token", "")
            if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
                raise DomainError("Form expired. Refresh and try again.", 400)

    @app.after_request
    def security_headers(response: Any) -> Any:
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
                "Referrer-Policy": "same-origin",
            }
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(DomainError)
    def domain_error(error: DomainError) -> ResponseReturnValue:
        return render_page("error.html", code=error.status, message=str(error)), error.status

    @app.errorhandler(OperationalError)
    def database_error(error: OperationalError) -> ResponseReturnValue:
        db.get_session().rollback()
        app.logger.error("Database unavailable: %s", type(error).__name__)
        return render_page(
            "error.html", code=503, message="Database unavailable. Retry in a moment."
        ), 503

    for code in (400, 403, 404, 413, 429):
        app.register_error_handler(
            code,
            lambda error: (
                render_page("error.html", code=error.code, message=error.description),
                error.code,
            ),
        )
    return app
