# Procurement v4: research and improvement plan

Research date: 21 October 2026. Historical research recorded before implementation. The subsequent upgrade is documented in README.md, scope.md and decisions.md; the recommendations below retain their original planning context.

## Updated brief

The supplied `Programming Test v4 (1).pdf` was read in full. Page 3 removes the two mandatory chat/mobile connectivity clauses present in the earlier Procurement brief. Python web application and SQLite/PostgreSQL remain required. Warehouse management and payment remain excluded. AI/Computer Vision for form input remains optional. Page 1 still evaluates analysis, code organization, database schema and debugging, and requests one repository, BPMN PDF and Excel WBS.

The previous copy-paste assumption is now obsolete. When implementing v4, update README, scope, BPMN builder/export and WBS together. Do not leave contradictory statements in the submission.

## Recommended direction

Keep Flask and the current UI. Evolve into a small modular monolith: one deployable Python application with clear modules. Use PostgreSQL for the main shared demo, SQLAlchemy for persistence and Alembic for versioned migrations. Keep SQLite only if its configuration and tests remain supported; otherwise document PostgreSQL as the sole supported engine, which the brief permits.

This is a project-specific recommendation, not a claim that PostgreSQL or Flask automatically improves hiring outcomes. SQLite is valid for this assessment and low-write-concurrency deployments. Choose PostgreSQL to demonstrate and test concurrent multi-user operations explicitly. Avoid a framework rewrite solely for appearance.

Suggested structure:

```text
procurement/
  __init__.py             App factory and registration
  config.py              Explicit local, test and deployment settings
  auth/                  Session endpoints and permission helpers
  requests/              Request routes, input schema and request operations
  purchasing/            Suppliers, quotations, selection and PO operations
  receiving/             Accepted delivery quantities and completion
  documents/             Protected upload, extraction and draft preview
  models.py              Relational models and constraints
  templates/
  static/
migrations/
tests/
  unit/
  integration/
  e2e/
docs/
```

Split by real responsibility. A small module can remain one file. Routes authenticate and validate transport input; operations enforce policy and own the transaction; persistence provides constraints and queries. No generic repository class, event bus or workflow engine is required. Use Python type annotations and explicit input objects so business rules do not depend on Flask form objects or global request state.

Flask officially supports app factories and Blueprints for modular applications. The existing factory is a useful starting point. [Flask factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/), [Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/).

## Gaps observed in the current source

These findings come from reading the actual application, not from running new tests in this research pass.

| Area | Current implementation | Recommended improvement |
| --- | --- | --- |
| Request editing | Draft items/date are fixed; revision changes purpose only | Allow owner to edit draft and returned requests. Record a revision number. Submission freezes the exact content reviewed. |
| Approval | Single-stage state transition with an audit note | Preserve single stage initially. Tie approval to a request revision; any material revision invalidates the old approval. |
| Purchasing | Supplier and quotation reference plus a single total | Store quotation lines and PO lines with agreed quantities, unit prices and units. Keep estimates separate from agreed prices. |
| Vendor choice | One seeded supplier is selected directly | Add a small supplier directory and comparison of manually recorded quotations with price, delivery lead time and selection rationale. One valid quotation remains allowed. |
| Receipts | Good quantity bounds and transaction protection | Retain partial receipts. Compare acceptance against PO quantities; display delivery-specific line quantities from receipt_items. |
| Retry safety | Duplicate state actions and delivery references rejected | Add operation tokens for create/receive with payload matching. Same token and payload returns the original result; changed payload is rejected. |
| Database evolution | CREATE TABLE IF NOT EXISTS only | Versioned migrations, tested on a clean database and across schema changes. |
| Dashboard | Loads all matching and all visible requests | Bounded pagination and SQL aggregate counts. Keep ownership restrictions in both list and summary queries. |
| Configuration | Local secret file generated even when test/env key is supplied | Resolve explicit configuration first; isolate test files and deployment secrets. Fail clearly on invalid deployment configuration. |
| Fixtures | Demo dates fixed in November/December 2026 | Use controlled relative dates so fresh setup does not fail as the calendar advances. Make fixture creation atomic or safely resumable. |
| Source clarity | Long SQL calls, compressed templates, untyped functions | Format source, introduce narrow helpers/partials where they remove duplication, annotate public interfaces. |
| Reviewability | Local tests and manual browser verification exist | Add reproducible CI and browser regression tests, clean-clone startup instructions and a short demo narrative. |

RFQ comparison is a useful domain reference rather than a mandatory rule: Odoo documents comparing vendor product lines, prices and lead times before confirmation. This does not require implementing an ERP, mandatory three-vendor bidding or automatic vendor emails. [Odoo alternative quotations](https://www.odoo.com/documentation/16.0/applications/inventory_and_mrp/purchase/manage_deals/calls_for_tenders.html).

## Database and transaction design

Proposed relationships: request -> request revision -> requested lines; revision -> approval decision; request -> quotations -> quotation lines; selected quotation -> PO -> PO lines; PO -> receipts -> receipt lines. Supplier data is referenced, while issued documents preserve relevant name/address and item/price snapshots so later edits cannot rewrite history. Record unit of measure explicitly. Use integer rupiah under an explicit IDR-only scope; define quantity precision separately if fractional units are supported.

Keep one selected supplier and one PO per request for the assessment. Multiple deliveries already demonstrate real workflow complexity. Multi-supplier split orders and PO amendments are later scope, not necessary infrastructure.

For receipt/approval mutations: begin transaction, lock the owning request or PO row, check revision/state/permissions, validate all lines, insert the operation record and audit event, update quantities/state, then commit. All operations on the same aggregate must acquire the same lock consistently. Database uniqueness and check constraints remain necessary. Transactions should not include model inference or document parsing.

PostgreSQL SELECT FOR UPDATE locks the selected row until transaction end; careless multiple-lock acquisition can deadlock. SQLite instead permits one writer at a time. The current BEGIN IMMEDIATE protection cannot simply be copied into a PostgreSQL adapter. Integration tests must use the database engine actually deployed. [PostgreSQL locking](https://www.postgresql.org/docs/current/explicit-locking.html), [SQLite suitability](https://www.sqlite.org/whentouse.html).

Stale browser edits should include an expected revision and return a clear conflict if the stored revision changed. SQLAlchemy version counters are one supported implementation, with documented limitations for bulk operations. Migrations should be reviewed even if initially autogenerated. [SQLAlchemy versioning](https://docs.sqlalchemy.org/en/20/orm/versioning.html), [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

Retry behavior is a design recommendation adapted from documented idempotent API practice. A duplicate error prevents repeated writes, while returning the first successful result also lets the user recover after a lost response. Token scope must include actor and operation, and payload reuse must be checked. [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests).

## One useful differentiator: quotation-to-form extraction

Recommended optional feature: upload a supplier quotation as PDF/JPG/PNG, extract supplier/reference/date/item/quantity/unit/price fields, review them beside the source, then populate an editable quotation draft. A person explicitly confirms saving; normal role, budget and approval rules still apply. No autonomous approval or supplier selection.

1. Restrict upload types and byte/page/pixel limits. Check actual type, generate storage names and keep documents outside the public static directory. Authorize upload and download separately.
2. Extract into an explicit schema; missing or ambiguous fields remain unknown. Strict validation checks numeric bounds and types, not semantic truth.
3. Show source evidence and mark fields requiring review. Do not present the model's self-reported confidence as measured accuracy.
4. Set provider timeout, file/cost limits and clear retry behavior. The rest of procurement remains usable if extraction fails or the provider is not configured.
5. Treat document contents and model outputs as untrusted. The extractor has no approval, database-write or vendor-contact tools.
6. Provide synthetic sample quotations with expected fields. Evaluate held-out documents and report actual field-level results, failures and corrections. Clearly label fixture/sample mode; do not describe prerecorded output as live AI.

These controls follow upload and model-output security guidance. Pydantic is a candidate schema validator, not evidence that extracted values are correct. [OWASP uploads](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [OWASP prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/).

## Testing and debugging evidence

Prioritize invariants: no self-approval; requester isolation; no ordering without current approval; PO price bounds; no over-receipt; no duplicate operations; rollback on failure; stale revisions rejected. Add two real users of the same role to test ownership, not only one fixture per role.

Add HTTP integration tests with independent request contexts and the deployment database. Browser scenarios should cover request revision -> resubmission -> approval -> PO -> partial and final receipt, failed form submission with inputs preserved, and extraction failure with manual entry still available. Keep failure screenshots and traces in CI artifacts rather than committing changing screenshots unnecessarily.

CI should check formatting/linting, typing, migrations and regression tests. Add a browser workflow with trace retention on failure. No arbitrary coverage target or large load-performance claim is needed. Include a short debugging note documenting a real reproduced problem, root cause, fix and regression test; never manufacture an incident. [GitHub Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), [Playwright pytest](https://playwright.dev/python/docs/test-runners).

Authorization must be enforced on every request, including document download, and deny unsupported access. Role, ownership and workflow state are separate checks. [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## Submission package and execution order

| Priority | Deliverable | Why it matters |
| --- | --- | --- |
| P0 | Update v4 requirement mapping and scope | Removes obsolete ambiguity; keeps PDF, WBS, code and tests aligned. |
| P0 | Editable drafts, revision-aware approval, PO lines | Fixes visible business limitations before optional polish. |
| P0 | Typed modules, migrations, repeatable setup and CI | Makes the engineering inspectable from a clean clone. |
| P1 | Quotation comparison, printable PO, detailed receipts | Shows procurement analysis through concrete decisions. |
| P1 | AI quotation extraction with review and failure handling | Implements the optional feature inside a useful workflow. |
| P1 | Short demo video, architecture/ERD, decision notes | Helps the reviewer verify the important behavior quickly. |
| P2 | Threshold approvals and operational overdue view | Add only if earlier work is complete and time remains. |

Recommended demo: revise a returned request, compare two quotations with different lead times, explain the supplier choice, issue a PO, accept a partial delivery, retry a receipt without duplication, complete acceptance, then inspect audit history. Demonstrate AI extraction and one failure/recovery path if implemented.

README should begin with what the application does, setup, demo accounts and links to required documents. Include a small requirement -> BPMN task -> WBS item -> code -> test mapping. Add a few short architecture decisions explaining the chosen stack, transaction boundaries, immutable issued documents and human review of AI drafts. These are submission recommendations, not claims about the employer's undisclosed selection criteria.

For hosting, use a production WSGI server and HTTPS; Flask's development server is for local development. Protect demo access, use synthetic documents, and do not commit the confidential brief or real vendor files. [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/index.html).

Avoid microservices, Kubernetes, CQRS/event sourcing, mandatory vector databases, an unrestricted agent, a framework rewrite and a separate SPA/API unless an actual requirement justifies them. Deadline is not stated in the PDF; reduce scope in the above order if time is short.
