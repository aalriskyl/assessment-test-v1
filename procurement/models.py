"""Relational records. Issued quotations and orders preserve their own line snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('requester','approver','purchasing','receiver')", name="ck_user_role"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True)
    role: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    contact: Mapped[str] = mapped_column(Text)


class PurchaseRequest(Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint("priority IN ('low','normal','high')", name="ck_request_priority"),
        CheckConstraint(
            "status IN ('draft','submitted','rejected','approved','ordered','partial','received','cancelled')",
            name="ck_request_status",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text)
    needed_by: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, index=True)
    revision: Mapped[int] = mapped_column(default=1, server_default="1")
    approved_revision: Mapped[int | None]
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, default=utc_now)


class RequestItem(Base):
    __tablename__ = "request_items"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_item_quantity"),
        CheckConstraint("unit_price BETWEEN 1 AND 100000000000", name="ck_item_price"),
        CheckConstraint(
            "received_quantity >= 0 AND received_quantity <= quantity", name="ck_item_received"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(default=1, server_default="1")
    unit: Mapped[str] = mapped_column(Text, default="unit", server_default="unit")
    quantity: Mapped[int]
    unit_price: Mapped[int] = mapped_column(BigInteger)
    received_quantity: Mapped[int] = mapped_column(default=0, server_default="0")


class RequestRevision(Base):
    __tablename__ = "request_revisions"
    __table_args__ = (UniqueConstraint("request_id", "revision", name="uq_revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    revision: Mapped[int]
    snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (UniqueConstraint("request_id", "revision", name="uq_approval_revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    revision: Mapped[int]
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "revision", "supplier_id", "reference", name="uq_quotation_reference"
        ),
        CheckConstraint("lead_days BETWEEN 0 AND 365", name="ck_quote_lead"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    revision: Mapped[int]
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    supplier_name: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(Text)
    lead_days: Mapped[int]
    note: Mapped[str] = mapped_column(Text)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class QuotationLine(Base):
    __tablename__ = "quotation_lines"
    __table_args__ = (
        UniqueConstraint("quotation_id", "request_item_id", name="uq_quote_item"),
        CheckConstraint("unit_price BETWEEN 1 AND 100000000000", name="ck_quote_price"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    request_item_id: Mapped[int] = mapped_column(ForeignKey("request_items.id"))
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int]
    unit_price: Mapped[int] = mapped_column(BigInteger)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (CheckConstraint("total > 0", name="ck_po_total"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    quotation_reference: Mapped[str] = mapped_column(Text)
    total: Mapped[int] = mapped_column(BigInteger)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    request_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    supplier_name: Mapped[str] = mapped_column(Text, default="", server_default="")
    supplier_contact: Mapped[str] = mapped_column(Text, default="", server_default="")
    selection_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "request_item_id", name="uq_order_item"),
        CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_order_quantity"),
        CheckConstraint(
            "unit_price IS NULL OR unit_price BETWEEN 1 AND 100000000000", name="ck_order_price"
        ),
        CheckConstraint(
            "received_quantity >= 0 AND received_quantity <= quantity", name="ck_order_received"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"))
    request_item_id: Mapped[int] = mapped_column(ForeignKey("request_items.id"))
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int]
    unit_price: Mapped[int | None] = mapped_column(BigInteger)
    received_quantity: Mapped[int] = mapped_column(default=0, server_default="0")


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("request_id", "delivery_reference", name="uq_delivery_reference"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    delivery_reference: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_receipt_quantity"),)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("request_items.id"), primary_key=True)
    quantity: Mapped[int]


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, index=True)
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (UniqueConstraint("actor_id", "token", name="uq_actor_operation"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    storage_name: Mapped[str] = mapped_column(Text, unique=True)
    original_name: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    extracted_json: Mapped[str] = mapped_column(Text, default="{}")
    extraction_mode: Mapped[str] = mapped_column(Text, default="manual")
    created_at: Mapped[str] = mapped_column(Text, default=utc_now)
