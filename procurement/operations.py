"""Atomic retry protection shared by the small set of write operations."""

from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import DomainError
from .models import AuditEvent, Operation, PurchaseRequest, User, utc_now


def lock_actor(database: Session, actor: User) -> None:
    current = database.scalar(select(User).where(User.id == actor.id).with_for_update())
    if current is None or current.role != actor.role:
        raise DomainError("Your access has changed. Sign in again.", 403)


def authorize(actor: User, role: str) -> None:
    if actor.role != role:
        raise DomainError("You do not have access to this action.", 403)


def fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def replay(database: Session, actor: User, token: str, payload: object) -> int | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", token):
        raise DomainError("Operation token is invalid. Refresh the form.", 400)
    operation = database.scalar(
        select(Operation).where(Operation.actor_id == actor.id, Operation.token == token)
    )
    if operation is None:
        return None
    if operation.payload_hash != fingerprint(payload):
        raise DomainError(
            "This operation token was already used with different input. Refresh the form.", 409
        )
    return operation.request_id


def remember(database: Session, actor: User, token: str, payload: object, request_id: int) -> None:
    database.add(
        Operation(
            actor_id=actor.id, token=token, payload_hash=fingerprint(payload), request_id=request_id
        )
    )


def check_version(record: PurchaseRequest, expected_version: int) -> None:
    if record.version != expected_version:
        raise DomainError(
            "This request changed in another session. Reload it before continuing.", 409
        )


def audit(
    database: Session, record: PurchaseRequest, actor: User, action: str, note: str = ""
) -> None:
    record.version += 1
    record.updated_at = utc_now()
    database.add(AuditEvent(request_id=record.id, actor_id=actor.id, action=action, note=note))
