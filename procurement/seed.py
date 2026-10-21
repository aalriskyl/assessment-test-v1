"""Atomic synthetic fixtures with relative dates; never overwrite a populated database."""

from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

from .db import transaction
from .errors import DomainError
from .models import (
    AuditEvent,
    OrderLine,
    PurchaseOrder,
    PurchaseRequest,
    Quotation,
    QuotationLine,
    Receipt,
    ReceiptItem,
    RequestItem,
    RequestRevision,
    Supplier,
    User,
)


def seed_demo() -> None:
    with transaction() as database:
        if database.scalar(select(func.count()).select_from(User)):
            raise DomainError(
                "Seed requires an empty database. Existing records were preserved.", 409
            )
        users = {}
        for name, role in [
            ("Alya Putri", "requester"),
            ("Bima Pratama", "approver"),
            ("Clara Wijaya", "purchasing"),
            ("Dimas Saputra", "receiver"),
        ]:
            user = User(
                name=name,
                email=f"{role}@demo.local",
                role=role,
                password_hash=generate_password_hash("Demo123!"),
            )
            database.add(user)
            database.flush()
            users[role] = user
        suppliers = [
            Supplier(name=name, contact=contact)
            for name, contact in [
                ("PT Sumber Teknologi", "sales@sumber.example"),
                ("CV Kantor Sejahtera", "sales@kantor.example"),
                ("PT Nusantara Supply", "sales@nusantara.example"),
            ]
        ]
        database.add_all(suppliers)
        database.flush()
        examples = [
            (
                "Laptop for the design team",
                "Equipment",
                "high",
                "Design team onboarding",
                "Laptop 14 inch, 16 GB RAM",
                2,
                12500000,
                "submitted",
            ),
            (
                "Ergonomic office chairs",
                "Office supplies",
                "normal",
                "Replace damaged workstation chairs",
                "Ergonomic office chair",
                6,
                1500000,
                "approved",
            ),
            (
                "Meeting room displays",
                "Equipment",
                "normal",
                "Equip new collaboration rooms",
                "43 inch display",
                3,
                4500000,
                "partial",
            ),
            (
                "Monthly stationery restock",
                "Office supplies",
                "low",
                "Consumables for operations",
                "Stationery bundle",
                10,
                250000,
                "received",
            ),
            (
                "Network access points",
                "IT infrastructure",
                "high",
                "Improve wireless coverage",
                "Wi-Fi access point",
                4,
                1800000,
                "draft",
            ),
            (
                "Premium lounge furniture",
                "Office supplies",
                "low",
                "Refresh visitor seating",
                "Lounge sofa",
                2,
                8500000,
                "rejected",
            ),
        ]
        for index, (
            title,
            category,
            priority,
            purpose,
            item_name,
            quantity,
            price,
            status,
        ) in enumerate(examples):
            record = PurchaseRequest(
                requester_id=users["requester"].id,
                title=title,
                category=category,
                priority=priority,
                purpose=purpose,
                needed_by=str(date.today() + timedelta(days=20 + index)),
                status=status,
                revision=1,
                version=1,
                approved_revision=1 if status in {"approved", "partial", "received"} else None,
            )
            database.add(record)
            database.flush()
            accepted = quantity if status == "received" else 1 if status == "partial" else 0
            item = RequestItem(
                request_id=record.id,
                revision=1,
                name=item_name,
                unit="unit",
                quantity=quantity,
                unit_price=price,
                received_quantity=accepted,
            )
            database.add(item)
            database.flush()
            database.add(
                AuditEvent(
                    request_id=record.id,
                    actor_id=users["requester"].id,
                    action="Demo fixture created",
                    note=f"Synthetic example in {status} state.",
                )
            )
            if status != "draft":
                database.add(
                    RequestRevision(
                        request_id=record.id,
                        revision=1,
                        snapshot=json.dumps(
                            {
                                "title": title,
                                "category": category,
                                "priority": priority,
                                "needed_by": record.needed_by,
                                "purpose": purpose,
                                "items": [
                                    {
                                        "name": item_name,
                                        "unit": "unit",
                                        "quantity": quantity,
                                        "unit_price": price,
                                    }
                                ],
                                "synthetic_fixture": True,
                            }
                        ),
                    )
                )
            if status not in {"approved", "partial", "received"}:
                continue
            quotes = []
            for supplier, unit_price, lead in [
                (suppliers[0], price - 10000, 5),
                (suppliers[1], price - 20000, 14),
            ]:
                quote = Quotation(
                    request_id=record.id,
                    revision=1,
                    supplier_id=supplier.id,
                    supplier_name=supplier.name,
                    reference=f"QUO-DEMO-{record.id}-{lead}",
                    lead_days=lead,
                    note="Synthetic supplier quotation.",
                )
                database.add(quote)
                database.flush()
                database.add(
                    QuotationLine(
                        quotation_id=quote.id,
                        request_item_id=item.id,
                        name=item.name,
                        unit=item.unit,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                )
                quotes.append(quote)
            if status == "approved":
                continue
            order = PurchaseOrder(
                request_id=record.id,
                supplier_id=suppliers[0].id,
                buyer_id=users["purchasing"].id,
                quotation_reference=quotes[0].reference,
                total=quantity * (price - 10000),
                quotation_id=quotes[0].id,
                request_revision=1,
                supplier_name=suppliers[0].name,
                supplier_contact=suppliers[0].contact,
                selection_reason="Faster delivery meets the required date.",
            )
            database.add(order)
            database.flush()
            database.add(
                OrderLine(
                    order_id=order.id,
                    request_item_id=item.id,
                    name=item.name,
                    unit=item.unit,
                    quantity=quantity,
                    unit_price=price - 10000,
                    received_quantity=accepted,
                )
            )
            receipt = Receipt(
                request_id=record.id,
                receiver_id=users["receiver"].id,
                delivery_reference=f"DO-DEMO-{record.id}",
                note="Synthetic inspected and accepted goods.",
            )
            database.add(receipt)
            database.flush()
            database.add(ReceiptItem(receipt_id=receipt.id, item_id=item.id, quantity=accepted))
