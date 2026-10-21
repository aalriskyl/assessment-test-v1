"""Restore the legacy unnamed PO check after SQLite batch recreation."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    checks = sa.inspect(op.get_bind()).get_check_constraints("purchase_orders")
    if not any("total" in check["sqltext"] and ">" in check["sqltext"] for check in checks):
        with op.batch_alter_table("purchase_orders") as batch:
            batch.create_check_constraint("ck_po_total", "total > 0")


def downgrade():
    raise RuntimeError("Restore a verified backup instead of weakening constraints.")
