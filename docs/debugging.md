# Reproduced defects and regression evidence

## Legacy PO check constraint lost during SQLite table recreation

Trigger: upgrade the v1 SQLite schema, whose purchase_orders table used an unnamed `CHECK(total > 0)`, while adding a quotation foreign key with Alembic batch operations.

Observation: Alembic reported that the unnamed check was omitted during recreation. Preserving rows alone did not prove that constraints survived.

Root cause: the original schema did not name its check constraint. SQLite batch recreation reflects and rebuilds the table; the unnamed check needed explicit preservation.

Fix: revision 0003 inspects existing checks and restores the positive-total constraint only when missing. Migration verification checks foreign keys before commit. New schema constraints have stable names.

Regression: `test_legacy_migration_preserves_total_and_unknown_line_prices` creates an actual v1 database, migrates it, verifies the original total/received quantity, checks that unknown agreed line prices remain null, and confirms that the PO total check exists.

## Duplicate full delivery by two receivers

Trigger: two different receiver users attempt to accept all remaining goods against the same order version.

Risk: independent reads followed by writes could both accept the same remaining quantities.

Control: each operation locks its actor and the owning request, checks the expected version after acquiring the request lock, and commits quantity changes, receipt records, operation token and audit atomically. SQLite serializes the writes with an immediate transaction.

Regression: `test_two_receivers_cannot_overreceive` runs two real threads. Exactly one succeeds, one conflicts, and only one receipt exists. The unchanged test runs against both supported database engines. This is a tested concurrency scenario, not a claim of load capacity.
