"""Baseline schema, also used to adopt the existing local v1 database."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.CheckConstraint(
            "role IN ('requester','approver','purchasing','receiver')", name="ck_user_role"
        ),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("contact", sa.Text, nullable=False),
    )
    op.create_table(
        "requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("requester_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        *[
            sa.Column(name, sa.Text, nullable=False)
            for name in [
                "title",
                "category",
                "priority",
                "needed_by",
                "purpose",
                "status",
                "created_at",
                "updated_at",
            ]
        ],
        sa.CheckConstraint("priority IN ('low','normal','high')", name="ck_request_priority"),
        sa.CheckConstraint(
            "status IN ('draft','submitted','rejected','approved','ordered','partial','received','cancelled')",
            name="ck_request_status",
        ),
    )
    op.create_table(
        "request_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.BigInteger, nullable=False),
        sa.Column("received_quantity", sa.Integer, server_default="0", nullable=False),
        sa.CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_item_quantity"),
        sa.CheckConstraint("unit_price BETWEEN 1 AND 100000000000", name="ck_item_price"),
        sa.CheckConstraint(
            "received_quantity >= 0 AND received_quantity <= quantity", name="ck_item_received"
        ),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "request_id", sa.Integer, sa.ForeignKey("requests.id"), nullable=False, unique=True
        ),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quotation_reference", sa.Text, nullable=False),
        sa.Column("total", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.CheckConstraint("total > 0", name="ck_po_total"),
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("receiver_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("delivery_reference", sa.Text, nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("request_id", "delivery_reference", name="uq_delivery_reference"),
    )
    op.create_table(
        "receipt_items",
        sa.Column("receipt_id", sa.Integer, sa.ForeignKey("receipts.id"), primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("request_items.id"), primary_key=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_receipt_quantity"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    for table, column in [
        ("requests", "requester_id"),
        ("requests", "status"),
        ("request_items", "request_id"),
        ("audit_events", "request_id"),
        ("login_attempts", "email"),
    ]:
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    raise RuntimeError("Destructive downgrades are disabled. Restore a verified backup instead.")
