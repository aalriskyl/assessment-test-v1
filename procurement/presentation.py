"""Publish explicit view data to React; Flask retains routing and authorization."""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from flask import (
    Response,
    current_app,
    g,
    get_flashed_messages,
    jsonify,
    render_template,
    request,
    session,
)
from pydantic import BaseModel
from sqlalchemy.engine import Row
from werkzeug.datastructures import MultiDict

from .models import (
    Document,
    OrderLine,
    PurchaseOrder,
    PurchaseRequest,
    Quotation,
    QuotationLine,
    RequestItem,
    RequestRevision,
    Supplier,
    User,
)
from .workflow import STATUS_LABELS


def public_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # PostgreSQL SUM(bigint) returns Decimal; view amounts are whole IDR.
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return int(value)
    if isinstance(value, MultiDict):
        return {key: value.getlist(key) for key in value if key != "password"}
    if isinstance(value, User):
        return {"id": value.id, "name": value.name, "role": value.role}
    if isinstance(value, Document):
        return {
            key: getattr(value, key)
            for key in (
                "id",
                "request_id",
                "original_name",
                "media_type",
                "extraction_mode",
            )
        }
    if isinstance(value, RequestRevision):
        return {"revision": value.revision, "created_at": value.created_at}
    if isinstance(
        value,
        (
            PurchaseRequest,
            RequestItem,
            OrderLine,
            PurchaseOrder,
            Supplier,
            Quotation,
            QuotationLine,
        ),
    ):
        return {column.name: getattr(value, column.name) for column in value.__table__.columns}
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Row):
        return public_value(dict(value._mapping))
    if isinstance(value, Mapping):
        return {key: public_value(item) for key, item in value.items() if not key.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [public_value(item) for item in value]
    raise TypeError(f"Unsupported view value: {type(value).__name__}")


def render_page(template: str, **context: Any) -> Response | str:
    session.setdefault("csrf_token", secrets.token_hex(32))
    # Never return submitted secrets (including a password) as form defaults.
    values = MultiDict(request.form)
    values.pop("password", None)
    context.setdefault("values", values)
    payload = {
        "page": template.removesuffix(".html"),
        "data": public_value(context),
        "user": public_value(g.get("user")),
        "csrfToken": session["csrf_token"],
        "statusLabels": STATUS_LABELS,
        "flashes": get_flashed_messages(with_categories=True),
    }
    if request.accept_mimetypes.best == "application/json":
        return jsonify(payload)
    manifest_path = Path(current_app.root_path) / "static/app/.vite/manifest.json"
    if not manifest_path.is_file():
        return current_app.response_class(
            "Frontend build missing. Run npm ci and npm run build in frontend/.", status=503
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["src/main.tsx"]
    return render_template("app.html", state=payload, entry=entry)
