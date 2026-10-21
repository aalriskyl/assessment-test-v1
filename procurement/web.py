"""HTTP routes adapt forms to typed operations and assemble read-only views."""

from __future__ import annotations

import json
import secrets
from urllib.parse import urlencode

from flask import Blueprint, flash, g, redirect, request, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from . import purchasing, receiving, workflow
from .auth import login_required
from .db import get_session
from .errors import DomainError
from .extraction import Extraction
from .inputs import CATEGORIES, integer, parse_request
from .models import (
    AuditEvent,
    Document,
    OrderLine,
    PurchaseOrder,
    Quotation,
    QuotationLine,
    Receipt,
    ReceiptItem,
    RequestItem,
    RequestRevision,
    Supplier,
    User,
)
from .presentation import render_page

bp = Blueprint("web", __name__)


def operation_fields() -> tuple[int, str]:
    return integer(request.form.get("version"), "Version", maximum=2_147_483_647), request.form.get(
        "operation_token", ""
    )


def new_token() -> str:
    return secrets.token_urlsafe(24)


@bp.get("/")
@login_required
def dashboard() -> ResponseReturnValue:
    if request.args:
        query = urlencode(
            {key: request.args[key] for key in ("q", "status", "page") if key in request.args}
        )
        return redirect(url_for("web.request_list") + (f"?{query}" if query else ""))
    return request_index(overview=True)


@bp.get("/requests")
@login_required
def request_list() -> ResponseReturnValue:
    return request_index(overview=False)


def request_index(*, overview: bool) -> ResponseReturnValue:
    page = integer(request.args.get("page", "1"), "Page", maximum=100000)
    search = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "")
    if status not in {"", "in_progress", "incoming", *workflow.STATUS_LABELS}:
        raise DomainError("Choose a valid request status.", 400)
    rows, total = workflow.list_requests(g.user, search, status, page)
    pages = max(1, (total + 14) // 15)
    if page > pages:
        return redirect(url_for("web.request_list", page=pages, q=search, status=status))
    return render_page(
        "dashboard" if overview else "requests",
        rows=rows,
        total=total,
        page=page,
        pages=pages,
        metrics=workflow.metrics(g.user),
        search=search,
        selected_status=status,
    )


@bp.route("/requests/new", methods=["GET", "POST"])
@login_required
def new_request() -> ResponseReturnValue:
    if g.user.role != "requester":
        raise DomainError("Only requesters can create requests.", 403)
    token = request.form.get("operation_token") or new_token()
    if request.method == "POST":
        try:
            request_id = workflow.create_request(g.user, parse_request(request.form), token)
            flash("Draft saved. Review it before submitting.", "success")
            return redirect(url_for("web.detail", request_id=request_id))
        except DomainError as error:
            flash(str(error), "error")
    return render_page(
        "request_form.html", values=request.form, record=None, token=token, categories=CATEGORIES
    )


@bp.route("/requests/<int:request_id>/edit", methods=["GET", "POST"])
@login_required
def edit_request(request_id: int) -> ResponseReturnValue:
    database = get_session()
    record = workflow.get_request(g.user, request_id)
    if g.user.role != "requester" or record.status not in {"draft", "rejected", "approved"}:
        raise DomainError("This request cannot be edited by your role in its current state.", 403)
    token = request.form.get("operation_token") or new_token()
    values = MultiDict(request.form)
    if request.method == "POST":
        try:
            version, _ = operation_fields()
            workflow.edit_request(
                g.user, request_id, parse_request(values), version, token, values.get("note", "")
            )
            flash("Revision saved. Submit the new draft for approval.", "success")
            return redirect(url_for("web.detail", request_id=request_id))
        except DomainError as error:
            flash(str(error), "error")
            if error.status == 409:
                return render_page("error.html", code=409, message=str(error)), 409
    else:
        for key in ("title", "category", "priority", "needed_by", "purpose"):
            values[key] = getattr(record, key)
        items = workflow.request_items(database, record)
        for key, field in [
            ("item_name", "name"),
            ("quantity", "quantity"),
            ("unit_price", "unit_price"),
            ("unit", "unit"),
        ]:
            values.setlist(key, [str(getattr(item, field)) for item in items])
    return render_page(
        "request_form.html", values=values, record=record, token=token, categories=CATEGORIES
    )


@bp.get("/requests/<int:request_id>")
@login_required
def detail(request_id: int) -> ResponseReturnValue:
    database = get_session()
    record = workflow.get_request(g.user, request_id)
    items = workflow.request_items(database, record)
    events = [
        dict(event.__dict__, name=name)
        for event, name in database.execute(
            select(AuditEvent, User.name)
            .join(User, User.id == AuditEvent.actor_id)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.id.desc())
        )
    ]
    quotes = []
    for quote in database.scalars(
        select(Quotation)
        .where(Quotation.request_id == request_id, Quotation.revision == record.revision)
        .order_by(Quotation.id)
    ):
        lines = list(
            database.scalars(
                select(QuotationLine)
                .where(QuotationLine.quotation_id == quote.id)
                .order_by(QuotationLine.id)
            )
        )
        quotes.append(
            dict(
                quote.__dict__,
                lines=lines,
                total=sum(line.unit_price * line.quantity for line in lines),
            )
        )
    receipts = []
    for receipt, name in database.execute(
        select(Receipt, User.name)
        .join(User, User.id == Receipt.receiver_id)
        .where(Receipt.request_id == request_id)
        .order_by(Receipt.id.desc())
    ):
        receipt_lines = database.execute(
            select(RequestItem.name, RequestItem.unit, ReceiptItem.quantity)
            .join(ReceiptItem, ReceiptItem.item_id == RequestItem.id)
            .where(ReceiptItem.receipt_id == receipt.id)
        ).all()
        receipts.append(dict(receipt.__dict__, name=name, lines=receipt_lines))
    order = database.scalar(select(PurchaseOrder).where(PurchaseOrder.request_id == request_id))
    order_lines = (
        list(
            database.scalars(
                select(OrderLine).where(OrderLine.order_id == order.id).order_by(OrderLine.id)
            )
        )
        if order
        else []
    )
    return render_page(
        "detail.html",
        record=record,
        requester=database.get(User, record.requester_id),
        total=sum(item.quantity * item.unit_price for item in items),
        items=items,
        events=events,
        quotes=quotes,
        receipts=receipts,
        order=order,
        order_lines=order_lines,
        token=new_token(),
        revisions=list(
            database.scalars(
                select(RequestRevision)
                .where(RequestRevision.request_id == request_id)
                .order_by(RequestRevision.revision.desc())
            )
        ),
    )


@bp.post("/requests/<int:request_id>/<action>")
@login_required
def perform_action(request_id: int, action: str) -> ResponseReturnValue:
    version, token = operation_fields()
    # Keep every domain failure visible as an HTTP failure; never hide conflicts in a 200.
    if action == "order":
        purchasing.issue_order(
            g.user,
            request_id,
            integer(request.form.get("quotation_id"), "Quotation", maximum=2_147_483_647),
            request.form.get("note", ""),
            version,
            token,
        )
    elif action == "receive":
        quantities = {
            key.removeprefix("received_"): value
            for key, value in request.form.items()
            if key.startswith("received_")
        }
        receiving.receive_goods(
            g.user,
            request_id,
            request.form.get("reference", ""),
            quantities,
            request.form.get("note", ""),
            version,
            token,
        )
    else:
        workflow.transition(
            g.user, request_id, action, version, token, request.form.get("note", "")
        )
    flash("Request updated successfully.", "success")
    return redirect(url_for("web.detail", request_id=request_id))


@bp.route("/requests/<int:request_id>/quotations/new", methods=["GET", "POST"])
@login_required
def quotation_form(request_id: int) -> ResponseReturnValue:
    database = get_session()
    record = workflow.get_request(g.user, request_id)
    if g.user.role != "purchasing" or record.status != "approved":
        raise DomainError("Quotations require purchasing access and an approved request.", 403)
    token = request.form.get("operation_token") or new_token()
    document = None
    extraction = None
    if request.form.get("document_id"):
        document = database.get(
            Document, integer(request.form["document_id"], "Document", maximum=2_147_483_647)
        )
        if document is None or document.request_id != request_id:
            raise DomainError("Document does not belong to this request.", 403)
        if document.extracted_json != "{}":
            extraction = Extraction.model_validate_json(document.extracted_json)
    if request.method == "POST":
        try:
            version, _ = operation_fields()
            if request.form.get("reviewed") != "yes":
                raise DomainError("Confirm that you checked the quotation against its source.")
            fields = {
                key: value
                for key, value in request.form.items()
                if key not in {"csrf_token", "operation_token", "version"}
            }
            purchasing.add_quotation(g.user, request_id, fields, version, token)
            flash("Quotation recorded. Compare it before selecting a supplier.", "success")
            return redirect(url_for("web.detail", request_id=request_id))
        except DomainError as error:
            flash(str(error), "error")
            if error.status == 409:
                return render_page("error.html", code=409, message=str(error)), 409
    return render_page(
        "quotation_form.html",
        record=record,
        items=workflow.request_items(database, record),
        suppliers=list(database.scalars(select(Supplier).order_by(Supplier.name))),
        values=request.form,
        token=token,
        extraction=extraction,
        document=document,
    )


@bp.get("/requests/<int:request_id>/order")
@login_required
def order_document(request_id: int) -> ResponseReturnValue:
    database = get_session()
    record = workflow.get_request(g.user, request_id)
    order = database.scalar(select(PurchaseOrder).where(PurchaseOrder.request_id == request_id))
    if order is None:
        raise DomainError("Purchase order not found.", 404)
    return render_page(
        "order.html",
        record=record,
        order=order,
        lines=list(
            database.scalars(
                select(OrderLine).where(OrderLine.order_id == order.id).order_by(OrderLine.id)
            )
        ),
    )


@bp.get("/requests/<int:request_id>/revisions/<int:revision>")
@login_required
def revision_document(request_id: int, revision: int) -> ResponseReturnValue:
    record = workflow.get_request(g.user, request_id)
    snapshot = get_session().scalar(
        select(RequestRevision).where(
            RequestRevision.request_id == request_id, RequestRevision.revision == revision
        )
    )
    if snapshot is None:
        raise DomainError("Revision not found.", 404)
    return render_page(
        "revision.html",
        record=record,
        snapshot=snapshot,
        content=json.loads(snapshot.snapshot),
    )


@bp.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers() -> ResponseReturnValue:
    if g.user.role != "purchasing":
        raise DomainError("Supplier directory requires purchasing access.", 403)
    if request.method == "POST":
        try:
            purchasing.add_supplier(
                g.user, request.form.get("name", ""), request.form.get("contact", "")
            )
            flash("Supplier added.", "success")
            return redirect(url_for("web.suppliers"))
        except DomainError as error:
            flash(str(error), "error")
    return render_page(
        "suppliers.html",
        suppliers=list(get_session().scalars(select(Supplier).order_by(Supplier.name))),
    )
