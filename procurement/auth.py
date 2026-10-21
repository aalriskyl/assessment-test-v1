from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, flash, g, redirect, request, session, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy import delete, func, select, text
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_session, transaction
from .errors import DomainError
from .models import LoginAttempt, User
from .presentation import render_page

bp = Blueprint("auth", __name__)
DUMMY_HASH = generate_password_hash("not-a-real-account")


def load_user() -> None:
    g.user = get_session().get(User, session["user_id"]) if session.get("user_id") else None


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        with transaction() as database:
            if database.bind is not None and database.bind.dialect.name == "postgresql":
                # Serialize the email bucket even before a login_attempt row exists.
                key = int.from_bytes(
                    hashlib.sha256(email.encode()).digest()[:8], "big", signed=True
                )
                database.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            database.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
            count = (
                database.scalar(
                    select(func.count())
                    .select_from(LoginAttempt)
                    .where(LoginAttempt.email == email)
                )
                or 0
            )
            if count >= 8:
                raise DomainError("Too many attempts. Try again in 15 minutes.", 429)
            database.add(LoginAttempt(email=email))
        user = get_session().scalar(select(User).where(User.email == email))
        password = request.form.get("password", "")
        valid = len(password) <= 256 and check_password_hash(
            user.password_hash if user else DUMMY_HASH, password
        )
        if user and valid:
            with transaction() as database:
                database.execute(delete(LoginAttempt).where(LoginAttempt.email == email))
            session.clear()
            session.update(user_id=user.id, csrf_token=secrets.token_hex(32), permanent=True)
            return redirect(url_for("web.dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_page("login.html")


@bp.post("/logout")
def logout() -> ResponseReturnValue:
    session.clear()
    return redirect(url_for("auth.login"))
