from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select

from .db import transaction
from .errors import DomainError
from .inputs import integer
from .models import OrderLine, PurchaseOrder, Receipt, ReceiptItem, RequestItem, User
from .operations import audit, authorize, check_version, lock_actor, remember, replay
from .workflow import get_request


def receive_goods(
    actor: User,
    request_id: int,
    reference: str,
    quantities: Mapping[str, str],
    note: str,
    expected_version: int,
    token: str,
) -> int:
    authorize(actor, "receiver")
    reference = reference.strip().upper()
    if not 1 <= len(reference) <= 100 or len(note) > 2000:
        raise DomainError(
            "Delivery reference is required (up to 100 characters); notes allow 2,000 characters."
        )
    payload = {
        "action": "receive",
        "request_id": request_id,
        "reference": reference,
        "quantities": dict(quantities),
        "note": note,
        "version": expected_version,
    }
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = get_request(actor, request_id, database, lock=True)
        check_version(record, expected_version)
        if record.status not in {"ordered", "partial"}:
            raise DomainError("This request has no outstanding delivery.", 409)
        if database.scalar(
            select(Receipt.id).where(
                Receipt.request_id == request_id,
                func.upper(Receipt.delivery_reference) == reference,
            )
        ):
            raise DomainError("This delivery reference has already been recorded.", 409)
        order = database.scalar(select(PurchaseOrder).where(PurchaseOrder.request_id == request_id))
        assert order is not None
        lines = list(
            database.scalars(
                select(OrderLine).where(OrderLine.order_id == order.id).order_by(OrderLine.id)
            )
        )
        allowed = {str(line.id) for line in lines}
        if set(quantities) - allowed:
            raise DomainError("Delivery contains an item outside this purchase order.")
        accepted = [
            (
                line,
                integer(
                    quantities.get(str(line.id), "0"), "Accepted quantity", minimum=0, maximum=10000
                ),
            )
            for line in lines
        ]
        if not any(quantity > 0 for _, quantity in accepted):
            raise DomainError("Record at least one inspected and accepted unit.")
        if any(quantity > line.quantity - line.received_quantity for line, quantity in accepted):
            raise DomainError("Accepted quantity exceeds the outstanding order quantity.")
        receipt = Receipt(
            request_id=request_id, receiver_id=actor.id, delivery_reference=reference, note=note
        )
        database.add(receipt)
        database.flush()
        for line, quantity in accepted:
            if quantity:
                line.received_quantity += quantity
                requested = database.get(RequestItem, line.request_item_id)
                assert requested is not None
                requested.received_quantity = line.received_quantity
                database.add(
                    ReceiptItem(
                        receipt_id=receipt.id, item_id=line.request_item_id, quantity=quantity
                    )
                )
        record.status = (
            "received"
            if all(line.received_quantity == line.quantity for line in lines)
            else "partial"
        )
        audit(database, record, actor, "Goods received", f"Delivery {reference}. {note}".strip())
        remember(database, actor, token, payload, request_id)
    return request_id
