"""Request lifecycle and query operations; no HTTP objects or global request state."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from .db import get_session, transaction
from .errors import DomainError
from .inputs import RequestInput
from .models import ApprovalDecision, PurchaseRequest, RequestItem, RequestRevision, User
from .operations import audit, authorize, check_version, lock_actor, remember, replay

STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Awaiting approval",
    "rejected": "Revision needed",
    "approved": "Approved",
    "ordered": "Ordered",
    "partial": "Partially received",
    "received": "Received",
    "cancelled": "Cancelled",
}


def get_request(
    actor: User, request_id: int, database: Session | None = None, lock: bool = False
) -> PurchaseRequest:
    database = database or get_session()
    query = select(PurchaseRequest).where(PurchaseRequest.id == request_id)
    if lock:
        query = query.with_for_update()
    record = database.scalar(query)
    if record is None:
        raise DomainError("Request not found.", 404)
    if actor.role == "requester" and record.requester_id != actor.id:
        raise DomainError("Request not found.", 404)
    if actor.role not in {"requester", "approver", "purchasing", "receiver"}:
        raise DomainError("Access denied.", 403)
    return record


def request_items(database: Session, record: PurchaseRequest) -> list[RequestItem]:
    return list(
        database.scalars(
            select(RequestItem)
            .where(RequestItem.request_id == record.id, RequestItem.revision == record.revision)
            .order_by(RequestItem.id)
        )
    )


def total_for(database: Session, record: PurchaseRequest) -> int:
    return sum(item.quantity * item.unit_price for item in request_items(database, record))


def create_request(actor: User, data: RequestInput, token: str) -> int:
    authorize(actor, "requester")
    payload = {"action": "create", "data": asdict(data)}
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = PurchaseRequest(
            requester_id=actor.id,
            title=data.title,
            category=data.category,
            priority=data.priority,
            needed_by=data.needed_by,
            purpose=data.purpose,
            status="draft",
            revision=1,
            version=1,
        )
        database.add(record)
        database.flush()
        for line in data.lines:
            database.add(RequestItem(request_id=record.id, revision=1, **asdict(line)))
        audit(database, record, actor, "Draft created", "Revision 1")
        remember(database, actor, token, payload, record.id)
        return record.id


def edit_request(
    actor: User, request_id: int, data: RequestInput, expected_version: int, token: str, note: str
) -> int:
    authorize(actor, "requester")
    if not note.strip() or len(note) > 2000:
        raise DomainError("Explain the changes in a revision note (up to 2,000 characters).")
    payload = {
        "action": "edit",
        "request_id": request_id,
        "data": asdict(data),
        "version": expected_version,
        "note": note,
    }
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = get_request(actor, request_id, database, lock=True)
        check_version(record, expected_version)
        if record.status not in {"draft", "rejected", "approved"}:
            raise DomainError(
                "Only a draft, returned or approved-but-unordered request can be edited.", 409
            )
        frozen = database.scalar(
            select(RequestRevision.id).where(
                RequestRevision.request_id == request_id,
                RequestRevision.revision == record.revision,
            )
        )
        if frozen:
            record.revision += 1
        else:
            database.execute(
                delete(RequestItem).where(
                    RequestItem.request_id == request_id, RequestItem.revision == record.revision
                )
            )
        for key in ("title", "category", "priority", "needed_by", "purpose"):
            setattr(record, key, getattr(data, key))
        record.status = "draft"
        record.approved_revision = None
        for line in data.lines:
            database.add(
                RequestItem(request_id=request_id, revision=record.revision, **asdict(line))
            )
        audit(
            database,
            record,
            actor,
            "Draft revised",
            f"Revision {record.revision}. Previous approval cleared. {note}",
        )
        remember(database, actor, token, payload, request_id)
    return request_id


def transition(
    actor: User, request_id: int, action: str, expected_version: int, token: str, note: str = ""
) -> int:
    rules = {
        "submit": ("requester", {"draft"}, "submitted"),
        "cancel": ("requester", {"draft", "submitted", "rejected", "approved"}, "cancelled"),
        "approve": ("approver", {"submitted"}, "approved"),
        "reject": ("approver", {"submitted"}, "rejected"),
    }
    if action not in rules:
        raise DomainError("Unknown action.", 404)
    role, states, next_state = rules[action]
    authorize(actor, role)
    if len(note) > 2000 or (action == "reject" and not note.strip()):
        raise DomainError("A return reason is required and notes must be at most 2,000 characters.")
    payload = {
        "action": action,
        "request_id": request_id,
        "version": expected_version,
        "note": note,
    }
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = get_request(actor, request_id, database, lock=True)
        check_version(record, expected_version)
        if record.status not in states:
            raise DomainError("This action is no longer available for the current status.", 409)
        if action in {"approve", "reject"}:
            if record.requester_id == actor.id:
                raise DomainError("You cannot review your own request.", 403)
            database.add(
                ApprovalDecision(
                    request_id=request_id,
                    revision=record.revision,
                    actor_id=actor.id,
                    decision=action,
                    note=note,
                )
            )
            record.approved_revision = record.revision if action == "approve" else None
        if action == "submit":
            if date.fromisoformat(record.needed_by) < date.today():
                raise DomainError("Required date has passed. Edit the draft before submitting.")
            lines = request_items(database, record)
            snapshot = {
                "title": record.title,
                "category": record.category,
                "priority": record.priority,
                "needed_by": record.needed_by,
                "purpose": record.purpose,
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "unit": item.unit,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                    }
                    for item in lines
                ],
            }
            database.add(
                RequestRevision(
                    request_id=request_id, revision=record.revision, snapshot=json.dumps(snapshot)
                )
            )
        record.status = next_state
        if action == "cancel":
            record.approved_revision = None
        labels = {
            "submit": "Submitted for approval",
            "cancel": "Cancelled",
            "approve": "Approved",
            "reject": "Revision requested",
        }
        audit(
            database, record, actor, labels[action], f"Revision {record.revision}. {note}".strip()
        )
        remember(database, actor, token, payload, request_id)
    return request_id


def list_requests(
    actor: User, search: str = "", status: str = "", page: int = 1
) -> tuple[list[dict], int]:
    database = get_session()
    totals = (
        select(
            RequestItem.request_id,
            RequestItem.revision,
            func.sum(RequestItem.quantity * RequestItem.unit_price).label("total"),
            func.count().label("item_count"),
        )
        .group_by(RequestItem.request_id, RequestItem.revision)
        .subquery()
    )
    query = (
        select(PurchaseRequest, User.name, totals.c.total, totals.c.item_count)
        .join(User, User.id == PurchaseRequest.requester_id)
        .join(
            totals,
            (totals.c.request_id == PurchaseRequest.id)
            & (totals.c.revision == PurchaseRequest.revision),
        )
    )
    conditions = []
    if actor.role == "requester":
        conditions.append(PurchaseRequest.requester_id == actor.id)
    if search:
        request_number = search.upper().removeprefix("PR-").lstrip("0") or "0"
        id_match = (
            PurchaseRequest.id == int(request_number)
            if request_number.isdigit() and len(request_number) < 10
            else PurchaseRequest.id == -1
        )
        conditions.append(or_(PurchaseRequest.title.ilike(f"%{search}%"), id_match))
    states = {
        "in_progress": ["approved", "ordered", "partial"],
        "incoming": ["ordered", "partial"],
    }.get(status, [status] if status else [])
    if states:
        conditions.append(PurchaseRequest.status.in_(states))
    query = query.where(*conditions)
    count = database.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = []
    for record, name, total, item_count in database.execute(
        query.order_by(PurchaseRequest.id.desc()).limit(15).offset((page - 1) * 15)
    ):
        rows.append(
            {
                column.name: getattr(record, column.name)
                for column in PurchaseRequest.__table__.columns
            }
            | {"requester_name": name, "total": total, "item_count": item_count}
        )
    return rows, count


def metrics(actor: User) -> dict[str, int]:
    query = select(PurchaseRequest.status, func.count()).group_by(PurchaseRequest.status)
    if actor.role == "requester":
        query = query.where(PurchaseRequest.requester_id == actor.id)
    counts = dict(get_session().execute(query).all())
    return {
        "total": sum(counts.values()),
        "pending": counts.get("submitted", 0),
        "active": sum(counts.get(state, 0) for state in ("approved", "ordered", "partial")),
        "received": counts.get("received", 0),
    }
