"""Opt-in browser regression: use a fresh seeded, disposable demo database."""

import os
import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "")
pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(not BASE_URL, reason="Set E2E_BASE_URL to a disposable seeded app."),
]


def login(page: Page, role: str) -> None:
    page.goto(BASE_URL + "/login")
    page.get_by_label("Email address").fill(f"{role}@demo.local")
    page.get_by_label("Password", exact=True).fill("Demo123!")
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_role("button", name="Sign out of workspace", exact=True)).to_be_visible()


def test_revision_quotation_order_and_partial_receipt(page: Page) -> None:
    from datetime import date, timedelta

    title = "Browser regression " + uuid4().hex[:8]
    login(page, "requester")
    page.get_by_role("link", name="New request", exact=True).click()
    page.get_by_label("Request title", exact=True).fill(title)
    page.get_by_label("Required by", exact=True).fill(str(date.today() + timedelta(days=30)))
    page.get_by_label("Business purpose", exact=True).fill("Synthetic browser regression")
    page.get_by_label("Item description", exact=True).fill("Monitor")
    page.get_by_label("Quantity", exact=True).fill("2")
    page.get_by_label("Unit price (IDR)", exact=True).fill("1000000")
    page.get_by_role("button", name="Save draft", exact=True).click()
    page.wait_for_url(re.compile(r"/requests/\d+$"))
    request_url = page.url
    page.get_by_role("button", name="Submit for approval", exact=True).click()
    page.get_by_role("button", name="Sign out of workspace", exact=True).click()
    login(page, "approver")
    page.goto(request_url)
    page.get_by_text("Request a revision", exact=True).click()
    page.get_by_label("What needs to change?", exact=True).fill("Clarify the business need")
    page.get_by_role("button", name="Return for revision", exact=True).click()
    page.get_by_role("button", name="Sign out of workspace", exact=True).click()
    login(page, "requester")
    page.goto(request_url)
    page.get_by_role("link", name="Edit request", exact=True).click()
    page.locator('textarea[name="purpose"]').fill("Two monitors for new operations workstations")
    page.get_by_label("Revision summary", exact=True).fill("Clarified business need")
    page.get_by_role("button", name="Save revision", exact=True).click()
    page.get_by_role("button", name="Submit for approval", exact=True).click()
    page.get_by_role("button", name="Sign out of workspace", exact=True).click()
    login(page, "approver")
    page.goto(request_url)
    page.get_by_role("button", name="Approve request", exact=True).click()
    page.get_by_role("button", name="Sign out of workspace", exact=True).click()
    login(page, "purchasing")
    page.goto(request_url)
    page.get_by_role("link", name="Add quotation manually", exact=True).click()
    page.locator('select[name="supplier_id"]').select_option(index=1)
    page.get_by_label("Quotation reference", exact=True).fill("Q-" + uuid4().hex[:8])
    page.get_by_label("Delivery lead time (days)", exact=True).fill("3")
    page.get_by_label("Unit price for Monitor", exact=True).fill("900000")
    page.locator('input[name="reviewed"]').check()
    page.get_by_role("button", name="Save reviewed quotation", exact=True).click()
    page.locator('select[name="quotation_id"]').select_option(index=1)
    page.get_by_label("Why this supplier?", exact=True).fill("Fits the budget and delivery date")
    page.get_by_role("button", name="Issue purchase order", exact=True).click()
    expect(page.get_by_role("link", name="View purchase order", exact=True)).to_be_visible()
    page.get_by_role("button", name="Sign out of workspace", exact=True).click()
    login(page, "receiver")
    page.goto(request_url)
    page.get_by_label("Delivery note reference", exact=True).fill("D-" + uuid4().hex[:8])
    delivery_reference = page.get_by_label("Delivery note reference", exact=True).input_value()
    page.get_by_label("Inspection note (optional)", exact=True).fill("Keep this inspection note")
    page.get_by_role("button", name="Confirm accepted goods", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text(
        "Record at least one inspected and accepted unit."
    )
    expect(page.get_by_label("Delivery note reference", exact=True)).to_have_value(
        delivery_reference
    )
    expect(page.get_by_label("Inspection note (optional)", exact=True)).to_have_value(
        "Keep this inspection note"
    )
    assert page.url == request_url
    page.locator('input[name^="received_"]').fill("1")
    page.get_by_role("button", name="Confirm accepted goods", exact=True).click()
    expect(page.get_by_text("Partially received", exact=True)).to_be_visible()
    page.get_by_label("Delivery note reference", exact=True).fill(delivery_reference)
    page.locator('input[name^="received_"]').fill("1")
    page.get_by_role("button", name="Confirm accepted goods", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text(
        "This delivery reference has already been recorded."
    )
    expect(page.get_by_role("status")).to_have_count(0)
    expect(page.get_by_label("Delivery note reference", exact=True)).to_have_value(
        delivery_reference
    )
    page.get_by_label("Delivery note reference", exact=True).fill("D-" + uuid4().hex[:8])
    page.locator('input[name^="received_"]').fill("1")
    page.get_by_role("button", name="Confirm accepted goods", exact=True).click()
    expect(page.get_by_role("heading", name="All goods received.", exact=True)).to_be_visible()


def test_mobile_navigation_and_logout(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    login(page, "requester")
    expect(page.get_by_role("button", name="Sign out of workspace", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("searchbox", name="Search requests").fill("Unapplied filter")
    page.locator('select[name="status"]').select_option("draft")
    page.get_by_role("link", name="Reset", exact=True).click()
    expect(page.get_by_role("searchbox", name="Search requests")).to_have_value("")
    expect(page.locator('select[name="status"]')).to_have_value("")
    page.get_by_role("link", name="New request", exact=True).click()
    expect(page.get_by_label("Request title", exact=True)).to_be_visible()


def test_filter_empty_results_and_line_item_controls(page: Page) -> None:
    login(page, "requester")
    page.get_by_role("searchbox", name="Search requests").fill("no-match-" + uuid4().hex)
    page.locator('select[name="status"]').select_option("received")
    page.get_by_role("button", name="Apply filters", exact=True).click()
    expect(page.get_by_role("heading", name="No requests here yet")).to_be_visible()
    page.get_by_role("link", name="Reset", exact=True).click()
    expect(page.get_by_role("searchbox", name="Search requests")).to_have_value("")
    expect(page.locator('select[name="status"]')).to_have_value("")
    page.get_by_role("link", name="New request", exact=True).click()
    expect(page.get_by_role("button", name="Remove item", exact=True)).to_be_disabled()
    page.get_by_label("Quantity", exact=True).fill("2")
    page.get_by_label("Unit price (IDR)", exact=True).fill("1000000")
    page.get_by_role("button", name="Add line item", exact=True).click()
    page.locator('input[name="quantity"]').nth(1).fill("3")
    page.locator('input[name="unit_price"]').nth(1).fill("50000")
    expect(page.locator("#estimated-total")).to_contain_text("2.150.000")
    page.get_by_role("button", name="Remove item", exact=True).nth(1).click()
    expect(page.locator("#estimated-total")).to_contain_text("2.000.000")
    for _ in range(19):
        page.get_by_role("button", name="Add line item", exact=True).click()
    expect(page.locator(".line-item")).to_have_count(20)
    expect(page.get_by_role("button", name="Add line item", exact=True)).to_be_disabled()
    page.get_by_role("link", name="Cancel", exact=True).click()
    expect(page.get_by_role("link", name="New request", exact=True)).to_be_visible()


def test_sidebar_route_state_and_browser_history(page: Page) -> None:
    login(page, "requester")
    navigation = page.get_by_role("navigation", name="Main navigation")
    active = navigation.locator('a[aria-current="page"]')
    expect(active).to_have_text("Overview")
    navigation.get_by_role("link", name="Purchase requests", exact=True).click()
    page.wait_for_url(BASE_URL + "/requests")
    expect(active).to_have_text("Purchase requests")
    expect(page.get_by_role("heading", name="Purchase requests", exact=True)).to_be_visible()
    page.reload()
    expect(active).to_have_text("Purchase requests")
    navigation.get_by_role("link", name="Approval queue", exact=True).click()
    expect(active).to_have_text("Approval queue")
    navigation.get_by_role("link", name="Incoming orders", exact=True).click()
    expect(active).to_have_text("Incoming orders")
    page.go_back()
    expect(active).to_have_text("Approval queue")
    page.go_forward()
    expect(active).to_have_text("Incoming orders")
    page.get_by_role("link", name="Reset", exact=True).click()
    page.wait_for_url(BASE_URL + "/requests")
    expect(active).to_have_text("Purchase requests")
    # Resetting an unchanged URL must not add a second copy to history.
    with page.expect_response(
        lambda response: response.url == BASE_URL + "/requests" and response.request.method == "GET"
    ):
        page.get_by_role("link", name="Reset", exact=True).click()
    expect(page.locator('main[aria-busy="false"]')).to_be_visible()
    page.go_back()
    expect(active).to_have_text("Incoming orders")


def test_offline_back_keeps_visible_form_and_route(page: Page) -> None:
    login(page, "requester")
    page.get_by_role("navigation", name="Main navigation").get_by_role(
        "link", name="Purchase requests", exact=True
    ).click()
    page.wait_for_url(BASE_URL + "/requests")
    page.get_by_role("link", name="New request", exact=True).click()
    page.get_by_label("Request title", exact=True).fill("Preserve this offline form")
    page.context.set_offline(True)
    try:
        page.go_back()
        expect(page.get_by_role("alert")).to_contain_text("Could not reach the server")
        expect(page).to_have_url(BASE_URL + "/requests/new")
        expect(page.get_by_label("Request title", exact=True)).to_have_value(
            "Preserve this offline form"
        )
    finally:
        page.context.set_offline(False)
    page.get_by_role("navigation", name="Main navigation").get_by_role(
        "link", name="Purchase requests", exact=True
    ).click()
    expect(page).to_have_url(BASE_URL + "/requests")
