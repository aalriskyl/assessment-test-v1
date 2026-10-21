from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select

from .db import transaction
from .errors import DomainError
from .inputs import integer, text
from .models import Document, OrderLine, PurchaseOrder, Quotation, QuotationLine, Supplier, User
from .operations import audit, authorize, check_version, lock_actor, remember, replay
from .workflow import get_request, request_items, total_for


def add_quotation(
    actor: User, request_id: int, data: Mapping[str, str], expected_version: int, token: str
) -> int:
    authorize(actor, "purchasing")
    payload = {
        "action": "quotation",
        "request_id": request_id,
        "data": dict(data),
        "version": expected_version,
    }
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = get_request(actor, request_id, database, lock=True)
        check_version(record, expected_version)
        if record.status != "approved" or record.approved_revision != record.revision:
            raise DomainError("A current approval is required before recording quotations.", 409)
        supplier = database.get(
            Supplier, integer(data.get("supplier_id"), "Supplier", maximum=2_147_483_647)
        )
        if supplier is None:
            raise DomainError("Select an existing supplier.")
        reference = text(data, "reference", "Quotation reference", 100).upper()
        if database.scalar(
            select(Quotation.id).where(
                Quotation.request_id == request_id,
                Quotation.revision == record.revision,
                Quotation.supplier_id == supplier.id,
                Quotation.reference == reference,
            )
        ):
            raise DomainError("This supplier quotation is already recorded.", 409)
        document_id = (
            integer(data["document_id"], "Document", maximum=2_147_483_647)
            if data.get("document_id")
            else None
        )
        if document_id:
            document = database.get(Document, document_id)
            if document is None or document.request_id != request_id:
                raise DomainError("Document does not belong to this request.", 403)
        quote = Quotation(
            request_id=request_id,
            revision=record.revision,
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            reference=reference,
            lead_days=integer(data.get("lead_days"), "Lead time", minimum=0, maximum=365),
            note=text(data, "note", "Quotation note", 2000, required=False),
            document_id=document_id,
        )
        database.add(quote)
        database.flush()
        for item in request_items(database, record):
            database.add(
                QuotationLine(
                    quotation_id=quote.id,
                    request_item_id=item.id,
                    name=item.name,
                    unit=item.unit,
                    quantity=item.quantity,
                    unit_price=integer(data.get(f"price_{item.id}"), f"Price for {item.name}"),
                )
            )
        audit(
            database,
            record,
            actor,
            "Quotation recorded",
            f"{supplier.name}: {reference}, revision {record.revision}.",
        )
        remember(database, actor, token, payload, request_id)
    return request_id


def issue_order(
    actor: User, request_id: int, quotation_id: int, reason: str, expected_version: int, token: str
) -> int:
    authorize(actor, "purchasing")
    if not reason.strip() or len(reason) > 2000:
        raise DomainError("Explain the supplier selection in up to 2,000 characters.")
    payload = {
        "action": "order",
        "request_id": request_id,
        "quotation_id": quotation_id,
        "reason": reason,
        "version": expected_version,
    }
    with transaction() as database:
        lock_actor(database, actor)
        existing = replay(database, actor, token, payload)
        if existing is not None:
            return existing
        record = get_request(actor, request_id, database, lock=True)
        check_version(record, expected_version)
        if record.status != "approved" or record.approved_revision != record.revision:
            raise DomainError("Order requires approval of the current request revision.", 409)
        quote = database.get(Quotation, quotation_id)
        if quote is None or quote.request_id != request_id or quote.revision != record.revision:
            raise DomainError("Select a quotation for the current request revision.")
        lines = list(
            database.scalars(
                select(QuotationLine)
                .where(QuotationLine.quotation_id == quotation_id)
                .order_by(QuotationLine.id)
            )
        )
        total = sum(line.quantity * line.unit_price for line in lines)
        if not lines or total > total_for(database, record):
            raise DomainError(
                "Quotation exceeds the approved budget. Revise and approve the request first."
            )
        supplier = database.get(Supplier, quote.supplier_id)
        assert supplier is not None
        order = PurchaseOrder(
            request_id=request_id,
            supplier_id=quote.supplier_id,
            buyer_id=actor.id,
            quotation_reference=quote.reference,
            total=total,
            quotation_id=quote.id,
            request_revision=record.revision,
            supplier_name=quote.supplier_name,
            supplier_contact=supplier.contact,
            selection_reason=reason,
        )
        database.add(order)
        database.flush()
        for line in lines:
            database.add(
                OrderLine(
                    order_id=order.id,
                    request_item_id=line.request_item_id,
                    name=line.name,
                    unit=line.unit,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                )
            )
        record.status = "ordered"
        audit(
            database,
            record,
            actor,
            "Purchase order issued",
            f"PO-{order.id:04d}, quotation {quote.reference}. {reason}",
        )
        remember(database, actor, token, payload, request_id)
    return request_id


def add_supplier(actor: User, name: str, contact: str) -> None:
    authorize(actor, "purchasing")
    if not 1 <= len(name.strip()) <= 120 or not 1 <= len(contact.strip()) <= 254:
        raise DomainError(
            "Supplier name and contact are required (maximum 120 and 254 characters)."
        )
    with transaction() as database:
        lock_actor(database, actor)
        if database.scalar(
            select(Supplier.id).where(func.lower(Supplier.name) == name.strip().lower())
        ):
            raise DomainError("A supplier with this name already exists.", 409)
        database.add(Supplier(name=name.strip(), contact=contact.strip()))
