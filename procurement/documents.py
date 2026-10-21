from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    request,
    send_file,
    url_for,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import func, select
from werkzeug.datastructures import MultiDict
from werkzeug.utils import secure_filename

from .auth import login_required
from .db import get_session, transaction
from .errors import DomainError
from .extraction import Extraction, extract_ai, extract_local_pdf, validate_file
from .models import Document, Supplier
from .operations import lock_actor
from .presentation import render_page
from .workflow import get_request, request_items

bp = Blueprint("documents", __name__)


@bp.route("/requests/<int:request_id>/documents", methods=["GET", "POST"])
@login_required
def upload(request_id: int) -> ResponseReturnValue:
    record = get_request(g.user, request_id)
    if g.user.role != "purchasing" or record.status != "approved":
        raise DomainError(
            "Document extraction requires purchasing access and an approved request.", 403
        )
    configured = bool(current_app.config["AI_API_KEY"] and current_app.config["AI_MODEL"])
    if request.method == "GET":
        return render_page("upload.html", record=record, configured=configured)
    mode = request.form.get("mode", "local")
    if mode not in {"local", "ai"}:
        raise DomainError("Choose an extraction method.")
    if mode == "ai" and (not configured or request.form.get("allow_external") != "yes"):
        raise DomainError(
            "Configure AI and explicitly allow sending this document to the provider."
        )
    upload = request.files.get("document")
    if upload is None or not upload.filename:
        raise DomainError("Choose a quotation document.")
    data, media_type, extension = validate_file(upload.read(5 * 1024 * 1024 + 1), upload.filename)
    if mode == "local" and media_type != "application/pdf":
        raise DomainError(
            "Local extraction supports text PDFs. Use AI for images or enter fields manually."
        )
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    storage_name = secrets.token_hex(24) + extension
    target = folder / storage_name
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with transaction() as database:
            lock_actor(database, g.user)
            latest = get_request(g.user, request_id, database, lock=True)
            if latest.status != "approved":
                raise DomainError("The request changed. Reopen it before uploading.", 409)
            count = (
                database.scalar(
                    select(func.count())
                    .select_from(Document)
                    .where(Document.uploader_id == g.user.id, Document.created_at >= cutoff)
                )
                or 0
            )
            if count >= 6:
                raise DomainError("Upload limit reached. Try again in 15 minutes.", 429)
            target.write_bytes(data)
            document = Document(
                request_id=request_id,
                uploader_id=g.user.id,
                storage_name=storage_name,
                original_name=(secure_filename(upload.filename) or "quotation")[:160],
                media_type=media_type,
                sha256=hashlib.sha256(data).hexdigest(),
                extraction_mode="pending",
            )
            database.add(document)
            database.flush()
            document_id = document.id
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    # File parsing / network calls happen after the upload transaction commits.
    try:
        extraction = (
            extract_ai(
                data, media_type, current_app.config["AI_API_KEY"], current_app.config["AI_MODEL"]
            )
            if mode == "ai"
            else extract_local_pdf(data)
        )
        extraction_json, extraction_mode = (
            extraction.model_dump_json(),
            "ai" if mode == "ai" else "local_pdf",
        )
    except DomainError as error:
        flash(str(error), "error")
        extraction_json, extraction_mode = "{}", "failed"
    with transaction() as database:
        stored = database.get(Document, document_id)
        assert stored is not None
        stored.extracted_json, stored.extraction_mode = extraction_json, extraction_mode
    return redirect(url_for("documents.review", document_id=document_id))


@bp.get("/documents/<int:document_id>/review")
@login_required
def review(document_id: int) -> ResponseReturnValue:
    database = get_session()
    document = database.get(Document, document_id)
    if document is None:
        raise DomainError("Document not found.", 404)
    record = get_request(g.user, document.request_id)
    if g.user.role != "purchasing" or record.status != "approved":
        raise DomainError("This document cannot be applied in the current request state.", 409)
    extraction = (
        Extraction.model_validate_json(document.extracted_json)
        if document.extracted_json != "{}"
        else None
    )
    suppliers = list(database.scalars(select(Supplier).order_by(Supplier.name)))
    values = MultiDict({"document_id": str(document.id)})
    if extraction:
        values["reference"] = extraction.reference or ""
        values["lead_days"] = str(extraction.lead_days) if extraction.lead_days is not None else ""
        matching = next(
            (
                supplier
                for supplier in suppliers
                if supplier.name.casefold() == (extraction.supplier or "").casefold()
            ),
            None,
        )
        if matching:
            values["supplier_id"] = str(matching.id)
    return render_page(
        "quotation_form.html",
        record=record,
        items=request_items(database, record),
        suppliers=suppliers,
        values=values,
        token=secrets.token_urlsafe(24),
        document=document,
        extraction=extraction,
    )


@bp.get("/documents/<int:document_id>/file")
@login_required
def download(document_id: int) -> ResponseReturnValue:
    document = get_session().get(Document, document_id)
    if document is None:
        raise DomainError("Document not found.", 404)
    get_request(g.user, document.request_id)
    target = Path(current_app.config["UPLOAD_FOLDER"]) / document.storage_name
    if not target.is_file():
        raise DomainError("The source document is no longer available.", 404)
    return send_file(
        target,
        mimetype=document.media_type,
        as_attachment=document.media_type == "application/pdf",
        download_name=document.original_name,
        conditional=False,
    )
