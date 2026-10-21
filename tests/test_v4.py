"""Run unchanged against isolated SQLite files or PostgreSQL schemas."""

from __future__ import annotations

import base64
import io
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from werkzeug.datastructures import MultiDict
from werkzeug.security import generate_password_hash

from procurement import create_app, db, purchasing, receiving, workflow
from procurement.errors import DomainError
from procurement.extraction import extract_ai, extract_local_pdf, validate_file
from procurement.inputs import parse_request
from procurement.models import (
    AuditEvent,
    Document,
    OrderLine,
    PurchaseOrder,
    Quotation,
    Receipt,
    RequestRevision,
    Supplier,
    User,
)

HASH = generate_password_hash("testpass")
ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / "tmp" / "tests-v4"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class Harness:
    def __init__(self, app):
        self.app = app
        self.users = {}
        with app.app_context(), db.transaction() as database:
            for key, role in [
                ("requester", "requester"),
                ("other", "requester"),
                ("approver", "approver"),
                ("purchasing", "purchasing"),
                ("receiver", "receiver"),
                ("receiver2", "receiver"),
            ]:
                user = User(name=key, email=f"{key}@test.local", role=role, password_hash=HASH)
                database.add(user)
                database.flush()
                self.users[key] = user
            supplier = Supplier(name="Supplier A", contact="a@example.test")
            database.add(supplier)
            database.flush()
            self.supplier_id = supplier.id
        self.form = MultiDict(
            {
                "title": "Team laptops",
                "category": "Equipment",
                "priority": "normal",
                "needed_by": str(date.today() + timedelta(days=30)),
                "purpose": "New hires",
            }
        )
        for key, values in {
            "item_name": ["Laptop", "Mouse"],
            "unit": ["unit", "unit"],
            "quantity": ["2", "3"],
            "unit_price": ["10000000", "100000"],
        }.items():
            self.form.setlist(key, values)
        self.data = parse_request(self.form)
        with app.app_context():
            self.id = workflow.create_request(self.users["requester"], self.data, uuid4().hex)

    def read(self):
        with self.app.app_context():
            return workflow.get_request(self.users["requester"], self.id)

    def rows(self, model):
        with self.app.app_context():
            return list(db.get_session().scalars(select(model)))

    def act(self, action, role=None, token=None, version=None, note=""):
        role = role or ("approver" if action in {"approve", "reject"} else "requester")
        with self.app.app_context():
            return workflow.transition(
                self.users[role],
                self.id,
                action,
                version or self.read().version,
                token or uuid4().hex,
                note,
            )

    def approve(self):
        self.act("submit")
        self.act("approve")

    def quote(self, price="9000000", token=None, reference=None):
        with self.app.app_context():
            record = workflow.get_request(self.users["purchasing"], self.id)
            fields = {
                "supplier_id": str(self.supplier_id),
                "reference": reference or uuid4().hex,
                "lead_days": "5",
                "note": "",
                "reviewed": "yes",
            }
            for item in workflow.request_items(db.get_session(), record):
                fields[f"price_{item.id}"] = price if item.name == "Laptop" else "80000"
            purchasing.add_quotation(
                self.users["purchasing"], self.id, fields, record.version, token or uuid4().hex
            )
            return db.get_session().scalar(select(Quotation.id).order_by(Quotation.id.desc()))

    def order(self, quotation_id=None, token=None, version=None):
        if self.read().status == "draft":
            self.approve()
        quotation_id = quotation_id or self.quote()
        with self.app.app_context():
            purchasing.issue_order(
                self.users["purchasing"],
                self.id,
                quotation_id,
                "Delivery meets the required date",
                version or self.read().version,
                token or uuid4().hex,
            )

    def receive(self, quantities=None, reference="DO-1", role="receiver", version=None, token=None):
        lines = self.rows(OrderLine)
        quantities = (
            quantities
            if quantities is not None
            else {str(line.id): str(line.quantity - line.received_quantity) for line in lines}
        )
        with self.app.app_context():
            return receiving.receive_goods(
                self.users[role],
                self.id,
                reference,
                quantities,
                "Inspected",
                version or self.read().version,
                token or uuid4().hex,
            )

    def login(self, client, role="requester"):
        client.environ_base["HTTP_ACCEPT"] = "application/json"
        response = client.get("/login")
        csrf = response.json["csrfToken"]
        return client.post(
            "/login",
            data={"csrf_token": csrf, "email": f"{role}@test.local", "password": "testpass"},
        )


@pytest.fixture
def harness():
    identifier = uuid4().hex
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-with-enough-length",
        "UPLOAD_FOLDER": str(TEMP_ROOT / identifier / "uploads"),
    }
    url = os.environ.get("TEST_DATABASE_URL")
    admin = None
    if url:
        parsed = make_url(url)
        if not parsed.database or not parsed.database.endswith("_test"):
            pytest.fail("TEST_DATABASE_URL must target a dedicated database ending in _test.")
        schema = f"test_{identifier}"
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        config.update(DATABASE_URL=url, DATABASE_SCHEMA=schema)
    else:
        config["DATABASE_URL"] = f"sqlite:///{TEMP_ROOT / (identifier + '.sqlite')}"
    app = create_app(config)
    with app.app_context():
        db.migrate()
    try:
        yield Harness(app)
    finally:
        app.extensions["engine"].dispose()
        if admin:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def test_complete_flow_and_order_price_snapshots(harness):
    h = harness
    h.order()
    assert h.rows(PurchaseOrder)[0].total == 18_240_000
    lines = h.rows(OrderLine)
    assert [line.unit_price for line in lines] == [9_000_000, 80_000]
    h.receive({str(lines[0].id): "1"})
    assert h.read().status == "partial"
    h.receive(reference="DO-2")
    assert h.read().status == "received"
    assert len(h.rows(Receipt)) == 2


def test_return_edit_all_fields_and_resubmit(harness):
    h = harness
    h.act("submit")
    h.act("reject", note="Clarify quantity")
    revised = replace(
        h.data, title="Updated laptop request", lines=(replace(h.data.lines[0], quantity=1),)
    )
    with h.app.app_context():
        workflow.edit_request(
            h.users["requester"], h.id, revised, h.read().version, uuid4().hex, "Only one hire"
        )
    assert h.read().revision == 2
    h.act("submit")
    h.act("approve")
    assert h.read().approved_revision == 2
    assert len(h.rows(RequestRevision)) == 2


def test_edit_after_approval_invalidates_old_quotes(harness):
    h = harness
    h.approve()
    old_quote = h.quote()
    with h.app.app_context():
        workflow.edit_request(
            h.users["requester"],
            h.id,
            replace(h.data, purpose="Changed need"),
            h.read().version,
            uuid4().hex,
            "Changed purpose",
        )
    assert h.read().approved_revision is None
    assert h.read().status == "draft"
    h.act("submit")
    h.act("approve")
    with pytest.raises(DomainError, match="current request revision"):
        h.order(old_quote)


def test_editing_after_order_is_denied(harness):
    h = harness
    h.order()
    with h.app.app_context(), pytest.raises(DomainError):
        workflow.edit_request(
            h.users["requester"], h.id, h.data, h.read().version, uuid4().hex, "change"
        )


def test_idempotent_create_and_mismatched_payload(harness):
    h = harness
    token = uuid4().hex
    with h.app.app_context():
        first = workflow.create_request(h.users["requester"], h.data, token)
        assert workflow.create_request(h.users["requester"], h.data, token) == first
        with pytest.raises(DomainError, match="different input"):
            workflow.create_request(h.users["requester"], replace(h.data, title="Different"), token)


def test_retry_receipt_returns_original_result(harness):
    h = harness
    h.order()
    quantities = {str(line.id): str(line.quantity) for line in h.rows(OrderLine)}
    version, token = h.read().version, uuid4().hex
    h.receive(quantities, version=version, token=token)
    h.receive(quantities, version=version, token=token)
    assert len(h.rows(Receipt)) == 1
    with pytest.raises(DomainError, match="different input"):
        h.receive(quantities, reference="CHANGED", version=version, token=token)


def test_two_receivers_cannot_overreceive(harness):
    h = harness
    h.order()
    version = h.read().version
    quantities = {str(line.id): str(line.quantity) for line in h.rows(OrderLine)}

    def deliver(role):
        try:
            h.receive(quantities, role=role, reference=role, version=version)
            return "accepted"
        except DomainError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(deliver, ["receiver", "receiver2"]))
    assert sorted(outcomes) == ["accepted", "conflict"]
    assert len(h.rows(Receipt)) == 1


@pytest.mark.parametrize("bad_quantity", ["-1", "NaN", "Infinity", "1.5", "3", "99999", "0"])
def test_bad_receipt_rolls_back_everything(harness, bad_quantity):
    h = harness
    h.order()
    lines = h.rows(OrderLine)
    before = len(h.rows(AuditEvent))
    with pytest.raises(DomainError):
        h.receive({str(lines[0].id): bad_quantity})
    assert not h.rows(Receipt)
    assert len(h.rows(AuditEvent)) == before
    assert all(line.received_quantity == 0 for line in h.rows(OrderLine))


def test_foreign_item_and_duplicate_delivery_denied(harness):
    h = harness
    h.order()
    with pytest.raises(DomainError):
        h.receive({"99999": "1"})
    line = h.rows(OrderLine)[0]
    h.receive({str(line.id): "1"}, reference="same")
    with pytest.raises(DomainError, match="already been recorded"):
        h.receive({str(line.id): "1"}, reference=" SAME ")


def test_quote_above_budget_and_unknown_supplier(harness):
    h = harness
    h.approve()
    quote = h.quote("11000000")
    with pytest.raises(DomainError, match="exceeds"):
        h.order(quote)
    assert not h.rows(PurchaseOrder)


def test_wrong_role_owner_and_stale_form(harness):
    h = harness
    with h.app.app_context(), pytest.raises(DomainError):
        workflow.get_request(h.users["other"], h.id)
    with pytest.raises(DomainError):
        h.act("approve", role="requester")
    stale = h.read().version
    h.act("submit")
    with pytest.raises(DomainError, match="another session"):
        h.act("approve", version=stale)


def test_request_filters_and_owner_aggregates(harness):
    h = harness
    h.approve()
    with h.app.app_context():
        assert workflow.metrics(h.users["other"])["total"] == 0
        assert workflow.list_requests(h.users["other"])[1] == 0
        assert workflow.list_requests(h.users["approver"], status="in_progress")[1] == 1
        assert workflow.list_requests(h.users["approver"], search=f"PR-{h.id:04d}")[1] == 1
        assert workflow.list_requests(h.users["approver"], search="' OR 1=1 --")[1] == 0


def test_dashboard_pagination_filters_and_reset(harness):
    h = harness
    with h.app.app_context():
        for number in range(17):
            workflow.create_request(
                h.users["requester"],
                replace(h.data, title=f"Pagination example {number:02d}"),
                uuid4().hex,
            )
    client = h.app.test_client()
    h.login(client)
    assert client.get("/").json["page"] == "dashboard"
    assert client.get("/requests").json["page"] == "requests"
    legacy = client.get("/?q=Pagination+example&status=draft")
    assert legacy.status_code == 302
    assert legacy.location == "/requests?q=Pagination+example&status=draft"
    page = client.get(legacy.location)
    assert page.json["data"]["total"] == 17
    assert page.json["data"]["pages"] == 2
    assert len(page.json["data"]["rows"]) == 15
    page = client.get("/requests?page=2&q=Pagination+example&status=draft")
    assert len(page.json["data"]["rows"]) == 2
    assert page.json["data"]["page"] == 2
    assert page.json["data"]["search"] == "Pagination example"
    assert page.json["data"]["selected_status"] == "draft"
    overflow = client.get("/requests?page=99&q=Pagination+example&status=draft")
    assert overflow.status_code == 302
    assert overflow.location == "/requests?page=2&q=Pagination+example&status=draft"
    empty = client.get("/requests?page=99&q=does-not-exist&status=received", follow_redirects=True)
    assert empty.json["data"]["page"] == 1
    assert empty.json["data"]["total"] == 0
    unfiltered = client.get("/requests")
    assert unfiltered.json["data"]["search"] == ""
    assert unfiltered.json["data"]["selected_status"] == ""
    assert client.get("/requests?status=unknown-status").status_code == 400


def test_http_csrf_role_checks_and_rendering(harness):
    h = harness
    client = h.app.test_client()
    assert client.get("/").status_code == 302
    assert client.post("/login").status_code == 400
    assert h.login(client).status_code == 302
    for route in ("/", "/requests", "/requests/new", f"/requests/{h.id}", f"/requests/{h.id}/edit"):
        assert client.get(route).status_code == 200
    page = client.get("/")
    assert page.headers["X-Frame-Options"] == "DENY"
    assert "object-src 'none'" in page.headers["Content-Security-Policy"]
    assert client.get("/suppliers").status_code == 403
    assert client.post(f"/requests/{h.id}/submit").status_code == 400


def test_react_state_keeps_credentials_private(harness):
    h = harness
    client = h.app.test_client()
    h.login(client)
    page = client.get(f"/requests/{h.id}")
    assert set(page.json["user"]) == {"id", "name", "role"}
    assert set(page.json["data"]["requester"]) == {"id", "name", "role"}
    assert h.users["requester"].password_hash not in page.get_data(as_text=True)
    other = h.app.test_client()
    other.environ_base["HTTP_ACCEPT"] = "application/json"
    login = other.get("/login")
    response = other.post(
        "/login",
        data={
            "csrf_token": login.json["csrfToken"],
            "email": "requester@test.local",
            "password": "never-return-this-password",
        },
    )
    assert "password" not in response.json["data"]["values"]
    assert "never-return-this-password" not in response.get_data(as_text=True)


def test_successful_form_edit_and_error_preserves_input(harness):
    h = harness
    client = h.app.test_client()
    h.login(client)
    page = client.get(f"/requests/{h.id}/edit")

    data = MultiDict(h.form)
    data.update(
        {
            "csrf_token": page.json["csrfToken"],
            "operation_token": page.json["data"]["token"],
            "version": str(page.json["data"]["record"]["version"]),
            "note": "Updated qty",
        }
    )
    data.setlist("quantity", ["0", "3"])
    response = client.post(f"/requests/{h.id}/edit", data=data)
    assert response.status_code == 200
    assert response.json["data"]["values"]["title"] == ["Team laptops"]
    data.setlist("quantity", ["1", "3"])
    assert client.post(f"/requests/{h.id}/edit", data=data).status_code == 302


def test_every_role_view_and_printable_po(harness):
    h = harness
    h.order()
    for role in ("requester", "approver", "purchasing", "receiver"):
        client = h.app.test_client()
        h.login(client, role)
        assert client.get(f"/requests/{h.id}").status_code == 200
        assert client.get(f"/requests/{h.id}/order").status_code == 200
        assert client.get(f"/requests/{h.id}/revisions/1").status_code == 200


def test_html_escape_and_login_throttling(harness):
    h = harness
    with h.app.app_context():
        identifier = workflow.create_request(
            h.users["requester"], replace(h.data, title="<script>alert(1)</script>"), uuid4().hex
        )
    client = h.app.test_client()
    h.login(client)
    html = client.get(f"/requests/{identifier}", headers={"Accept": "text/html"}).data
    assert b"<script>alert(1)</script>" not in html
    assert rb"\u003cscript\u003e" in html
    other = h.app.test_client()
    other.get("/login")
    with other.session_transaction() as current:
        token = current["csrf_token"]
    for _ in range(8):
        assert (
            other.post(
                "/login",
                data={"csrf_token": token, "email": "none@test.local", "password": "wrong"},
            ).status_code
            == 200
        )
    assert (
        other.post(
            "/login", data={"csrf_token": token, "email": "none@test.local", "password": "wrong"}
        ).status_code
        == 429
    )


def test_parse_request_rejects_misaligned_or_invalid_data(harness):
    data = MultiDict(harness.form)
    data.setlist("unit_price", ["NaN"])
    with pytest.raises(DomainError):
        parse_request(data)
    data = MultiDict(harness.form)
    data["needed_by"] = "2000-01-01"
    with pytest.raises(DomainError):
        parse_request(data)


def make_pdf(
    content="Supplier: Supplier A\nReference: QUO-1\nLead days: 5\nItem: Laptop | 2 | unit | 9000000",
):
    from reportlab.pdfgen.canvas import Canvas

    output = io.BytesIO()
    canvas = Canvas(output)
    y = 800
    for line in content.splitlines():
        canvas.drawString(40, y, line)
        y -= 20
    canvas.save()
    return output.getvalue()


def test_local_pdf_extraction_is_explicit_not_ai():
    data = make_pdf()
    assert validate_file(data, "quote.pdf")[1] == "application/pdf"
    extracted = extract_local_pdf(data)
    assert extracted.supplier == "Supplier A"
    assert extracted.lines[0].unit_price == 9000000
    assert "not AI" in extracted.warnings[0]
    assert extract_local_pdf(make_pdf("Unknown layout")).lines == []


@pytest.mark.parametrize(
    "data,name",
    [
        (b"<script>bad</script>", "quote.pdf"),
        (b"not an image", "quote.png"),
        (b"x", "quote.exe"),
        (b"", "empty.pdf"),
    ],
)
def test_upload_rejects_spoofed_types(data, name):
    with pytest.raises(DomainError):
        validate_file(data, name)


def test_ai_invalid_output_and_timeout_are_safe():
    with patch("procurement.extraction.requests.post", side_effect=__import__("requests").Timeout):
        with pytest.raises(DomainError, match="Manual entry"):
            extract_ai(b"fake-pdf", "application/pdf", "test-only", "gemini-test")
    with pytest.raises(DomainError, match="not configured"):
        extract_ai(b"x", "application/pdf", "", "")


def test_document_review_manual_fallback_and_download_permissions(harness):
    h = harness
    h.approve()
    client = h.app.test_client()
    h.login(client, "purchasing")
    client.get(f"/requests/{h.id}/documents")
    with client.session_transaction() as current:
        token = current["csrf_token"]
    response = client.post(
        f"/requests/{h.id}/documents",
        data={
            "csrf_token": token,
            "mode": "local",
            "document": (io.BytesIO(make_pdf()), "quote.pdf"),
        },
    )
    assert response.status_code == 302
    review = client.get(response.location)
    assert review.json["data"]["document"]["extraction_mode"] == "local_pdf"
    document = h.rows(Document)[0]
    fields = {
        "csrf_token": token,
        "operation_token": uuid4().hex,
        "version": str(h.read().version),
        "document_id": str(document.id),
        "supplier_id": str(h.supplier_id),
        "reference": "   ",
        "lead_days": "5",
        "reviewed": "yes",
    }
    invalid_quote = client.post(f"/requests/{h.id}/quotations/new", data=fields)
    assert "Quotation reference is required" in invalid_quote.json["flashes"][0][1]
    assert invalid_quote.json["data"]["document"]["id"] == document.id
    assert invalid_quote.json["data"]["extraction"]["lines"][0]["name"] == "Laptop"
    assert "storage_name" not in invalid_quote.json["data"]["document"]
    assert "extracted_json" not in invalid_quote.json["data"]["document"]
    fields["document_id"] = "99999999"
    assert client.post(f"/requests/{h.id}/quotations/new", data=fields).status_code == 403
    other = h.app.test_client()
    h.login(other, "other")
    assert other.get(f"/documents/{document.id}/file").status_code == 404
    assert client.get(f"/documents/{document.id}/file").status_code == 200
    (Path(h.app.config["UPLOAD_FOLDER"]) / document.storage_name).unlink()
    assert client.get(f"/documents/{document.id}/file").status_code == 404


def test_invalid_form_keeps_original_version_until_explicit_reload(harness):
    h = harness
    client = h.app.test_client()
    h.login(client)
    client.get(f"/requests/{h.id}/edit")
    with client.session_transaction() as current:
        csrf = current["csrf_token"]
    original_version = h.read().version
    with h.app.app_context():
        workflow.edit_request(
            h.users["requester"],
            h.id,
            replace(h.data, title="Changed elsewhere"),
            original_version,
            uuid4().hex,
            "Another tab edited the draft",
        )
    fields = MultiDict(h.form)
    fields.update(
        {
            "csrf_token": csrf,
            "operation_token": uuid4().hex,
            "version": str(original_version),
            "note": "My edits",
        }
    )
    fields["purpose"] = " "
    response = client.post(f"/requests/{h.id}/edit", data=fields)
    assert response.json["data"]["values"]["version"] == [str(original_version)]
    fields["purpose"] = "Valid purpose"
    assert client.post(f"/requests/{h.id}/edit", data=fields).status_code == 409
    assert h.read().title == "Changed elsewhere"


def test_clean_migration_and_second_run_are_safe(harness):
    h = harness
    with h.app.app_context():
        db.migrate()
        assert "order_lines" in inspect(db.get_engine()).get_table_names()
    assert h.read().title == "Team laptops"


def test_legacy_migration_preserves_total_and_unknown_line_prices():
    target = TEMP_ROOT / (uuid4().hex + "-legacy.sqlite")
    with sqlite3.connect(target) as connection:
        connection.executescript((ROOT / "procurement/schema.sql").read_text())
        connection.execute(
            "INSERT INTO users VALUES (1,'Legacy','legacy@test.local','requester',?)", (HASH,)
        )
        connection.execute(
            "INSERT INTO suppliers VALUES (1,'Legacy Supplier','legacy@example.test')"
        )
        connection.execute(
            "INSERT INTO requests(id,requester_id,title,category,priority,needed_by,purpose,status) VALUES (1,1,'Legacy','Equipment','normal','2099-01-01','Legacy request','partial')"
        )
        connection.execute("INSERT INTO request_items VALUES (1,1,'Item',2,100,1)")
        connection.execute(
            "INSERT INTO purchase_orders(id,request_id,supplier_id,buyer_id,quotation_reference,total) VALUES (1,1,1,1,'Q-OLD',180)"
        )
    app = create_app(
        {"SECRET_KEY": "test-secret-long-enough", "DATABASE_URL": f"sqlite:///{target}"}
    )
    with app.app_context():
        db.migrate()
        assert db.get_session().get(PurchaseOrder, 1).total == 180
        line = db.get_session().scalar(select(OrderLine))
        assert line.received_quantity == 1 and line.unit_price is None
        checks = inspect(db.get_engine()).get_check_constraints("purchase_orders")
        assert any("total" in check["sqltext"] for check in checks)
    client = app.test_client()
    with client.session_transaction() as current:
        current["user_id"] = 1
    revision = client.get("/requests/1/revisions/1", headers={"Accept": "application/json"})
    assert revision.status_code == 200
    assert revision.json["data"]["content"]["legacy_reconstructed"] is True
    assert revision.json["data"]["content"]["request"]["purpose"] == "Legacy request"
    app.extensions["engine"].dispose()


def test_receipt_database_failure_rolls_back_insert_and_quantities(harness):
    h = harness
    h.order()
    with patch("procurement.receiving.audit", side_effect=RuntimeError("injected failure")):
        with pytest.raises(RuntimeError):
            h.receive()
    assert not h.rows(Receipt)
    assert all(line.received_quantity == 0 for line in h.rows(OrderLine))
    assert h.read().status == "ordered"


def test_self_approval_and_cancellation_before_order(harness):
    h = harness
    h.act("submit")
    version = h.read().version
    with h.app.app_context(), db.transaction() as database:
        record = workflow.get_request(h.users["approver"], h.id, database, lock=True)
        record.requester_id = h.users["approver"].id
    with pytest.raises(DomainError, match="own request"):
        h.act("approve", version=version)
    with h.app.app_context(), db.transaction() as database:
        record = workflow.get_request(h.users["approver"], h.id, database, lock=True)
        record.requester_id = h.users["requester"].id
    h.act("approve")
    h.act("cancel")
    assert h.read().status == "cancelled"


@pytest.mark.parametrize("media_type", ["application/pdf", "image/png"])
def test_ai_schema_success_and_invalid_output(media_type):
    from unittest.mock import Mock

    output = {
        "supplier": "Supplier A",
        "reference": "Q1",
        "lead_days": 3,
        "lines": [
            {
                "name": "Laptop",
                "quantity": 2,
                "unit": "unit",
                "unit_price": 9000000,
                "evidence": "Laptop 2 x 9000000",
            }
        ],
        "warnings": [],
    }
    response = Mock(ok=True)
    response.json.return_value = {
        "status": "completed",
        "steps": [
            {"type": "thought", "signature": "unused-test-signature"},
            {"type": "model_output", "content": [{"type": "text", "text": json.dumps(output)}]},
        ],
    }
    with patch("procurement.extraction.requests.post", return_value=response) as post:
        assert (
            extract_ai(b"test", media_type, "test-only", "gemini-test").lines[0].unit_price
            == 9000000
        )
        assert post.call_args.args[0] == "https://generativelanguage.googleapis.com/v1/interactions"
        assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "test-only"
        assert post.call_args.kwargs["allow_redirects"] is False
        payload = json.loads(post.call_args.kwargs["data"])
        assert "tools" not in payload and payload["store"] is False
        assert payload["model"] == "gemini-test"
        assert payload["input"][0]["type"] == "user_input"
        inline = payload["input"][0]["content"][1]
        assert inline["type"] == ("document" if media_type == "application/pdf" else "image")
        assert inline["mime_type"] == media_type and base64.b64decode(inline["data"]) == b"test"
        schema = payload["response_format"]["schema"]
        assert schema["additionalProperties"] is False
        assert "unit_price" in schema["$defs"]["ExtractedLine"]["properties"]
    response.json.return_value = {
        "status": "completed",
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": '{"unexpected": true}'}]}
        ],
    }
    with (
        patch("procurement.extraction.requests.post", return_value=response),
        pytest.raises(DomainError),
    ):
        extract_ai(b"test", media_type, "test-only", "gemini-test")


@pytest.mark.parametrize(
    "result",
    [
        [],
        {"status": "failed", "error": {"message": "blocked"}},
        {"status": "incomplete", "steps": [{"type": "model_output", "content": []}]},
        {"status": "completed", "steps": [{"type": "function_call", "name": "approve"}]},
        {"status": "completed", "steps": [{"type": "model_output", "content": "invalid"}]},
    ],
)
def test_gemini_blocked_truncated_or_malformed_response_is_rejected(result):
    from unittest.mock import Mock

    response = Mock(ok=True)
    response.json.return_value = result
    with (
        patch("procurement.extraction.requests.post", return_value=response),
        pytest.raises(DomainError, match="Manual entry"),
    ):
        extract_ai(b"test", "application/pdf", "test-only", "gemini-test")


@pytest.mark.parametrize("status_code", [400, 403, 429, 500, 503])
def test_gemini_http_failure_keeps_manual_fallback(status_code):
    from unittest.mock import Mock

    with (
        patch(
            "procurement.extraction.requests.post",
            return_value=Mock(ok=False, status_code=status_code),
        ),
        pytest.raises(DomainError, match="manually"),
    ):
        extract_ai(b"test", "application/pdf", "test-only", "gemini-test")


def test_gemini_upload_requires_consent_and_only_prefills_review(harness):
    from unittest.mock import Mock

    h = harness
    h.approve()
    h.app.config.update(AI_API_KEY="server-only-test-key", AI_MODEL="gemini-test")
    client = h.app.test_client()
    h.login(client, "purchasing")
    page = client.get(f"/requests/{h.id}/documents")
    assert page.json["data"]["configured"] is True
    assert "server-only-test-key" not in page.get_data(as_text=True)
    payload = {"csrf_token": page.json["csrfToken"], "mode": "ai"}
    with patch("procurement.extraction.requests.post") as post:
        denied = client.post(
            f"/requests/{h.id}/documents",
            data={**payload, "document": (io.BytesIO(make_pdf()), "quote.pdf")},
        )
        assert denied.status_code == 422
        post.assert_not_called()
    output = {
        "supplier": "Supplier A",
        "reference": "GEMINI-Q1",
        "lead_days": 2,
        "lines": [
            {
                "name": "Laptop",
                "quantity": 2,
                "unit": "unit",
                "unit_price": 9000000,
                "evidence": "Laptop 2 x 9000000",
            }
        ],
        "warnings": [],
    }
    response = Mock(ok=True)
    response.json.return_value = {
        "status": "completed",
        "steps": [
            {"type": "thought", "signature": "unused-test-signature"},
            {"type": "model_output", "content": [{"type": "text", "text": json.dumps(output)}]},
        ],
    }
    with patch("procurement.extraction.requests.post", return_value=response):
        uploaded = client.post(
            f"/requests/{h.id}/documents",
            data={
                **payload,
                "allow_external": "yes",
                "document": (io.BytesIO(make_pdf()), "quote.pdf"),
            },
        )
    assert uploaded.status_code == 302
    review = client.get(uploaded.location)
    assert review.json["page"] == "quotation_form"
    assert review.json["data"]["values"]["reference"] == ["GEMINI-Q1"]
    assert review.json["data"]["extraction"]["lines"][0]["unit_price"] == 9000000
    assert h.rows(Document)[0].extraction_mode == "ai"
    assert h.read().status == "approved" and h.rows(Quotation) == []


def test_failed_document_extraction_still_opens_manual_form(harness):
    h = harness
    h.approve()
    client = h.app.test_client()
    h.login(client, "purchasing")
    with client.session_transaction() as current:
        token = current["csrf_token"]
    with patch(
        "procurement.documents.extract_local_pdf", side_effect=DomainError("Unreadable layout")
    ):
        response = client.post(
            f"/requests/{h.id}/documents",
            data={
                "csrf_token": token,
                "mode": "local",
                "document": (io.BytesIO(make_pdf()), "quote.pdf"),
            },
        )
    assert response.status_code == 302
    manual_form = client.get(response.location)
    assert manual_form.json["data"]["document"]["extraction_mode"] == "failed"
    assert manual_form.json["page"] == "quotation_form"
    assert h.rows(Document)[0].extraction_mode == "failed"


def test_seed_is_atomic_relative_and_preserves_existing_data(harness):
    from procurement.seed import seed_demo

    h = harness
    with h.app.app_context(), pytest.raises(DomainError, match="empty database"):
        seed_demo()
    assert len(h.rows(User)) == 6


def test_server_requires_quotation_review_confirmation(harness):
    h = harness
    h.approve()
    client = h.app.test_client()
    h.login(client, "purchasing")
    with client.session_transaction() as current:
        token = current["csrf_token"]
    response = client.post(
        f"/requests/{h.id}/quotations/new",
        data={
            "csrf_token": token,
            "version": str(h.read().version),
            "operation_token": uuid4().hex,
        },
    )
    assert "Confirm that you checked" in response.json["flashes"][0][1]
    assert not h.rows(Quotation)
