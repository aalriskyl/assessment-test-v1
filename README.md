# Procure

A procurement application for Programming Test v4, with a Python/Flask backend and a modular React + TypeScript frontend using shadcn/ui. It follows a request through revision, approval, supplier quotation comparison, itemized purchase order and accepted deliveries.

## Quick start

Run the commands from the repository root in PowerShell, using Python 3.12. SQLite works without an additional service. The built frontend is included, so Node is only needed when changing or rebuilding frontend source.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py migrate
.\.venv\Scripts\python.exe run.py seed-demo
.\.venv\Scripts\python.exe run.py serve
```

Open http://127.0.0.1:5000. `serve` uses Waitress on loopback. `python run.py` is an alternative local Flask development server. The seed is atomic, uses relative dates, and refuses to overwrite a populated database. Migrations never seed or erase records.

| Role | Email | Demo password |
| --- | --- | --- |
| Requester | requester@demo.local | Demo123! |
| Approver | approver@demo.local | Demo123! |
| Purchasing | purchasing@demo.local | Demo123! |
| Receiver | receiver@demo.local | Demo123! |

These are synthetic local demo accounts. Credentials are documented here rather than displayed in the application. Do not expose these fixtures as an unrestricted public service.

## Frontend development

Use Node 24 and the locked dependencies:

```powershell
cd frontend
npm.cmd ci
npm.cmd run build
npm.cmd test
cd ..
```

Flask serves the resulting hashed assets from `procurement/static/app`; no second production server or CORS configuration is needed. Reload after rebuilding. See [frontend architecture](frontend/README.md) for feature boundaries and the view-data contract. Displayed timestamps use **WIB (Asia/Jakarta)**; database timestamps stay UTC. Required delivery dates remain calendar dates.

## PostgreSQL

PostgreSQL and SQLite are supported by the same operations and regression suite. Set the environment before migrations and startup:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://procure:password@localhost:5432/procure'
.\.venv\Scripts\python.exe run.py migrate
.\.venv\Scripts\python.exe run.py seed-demo
.\.venv\Scripts\python.exe run.py serve
```

Without `DATABASE_URL`, the application uses `instance/procurement.sqlite`. Local dependency caches and existing demo databases are not needed by a fresh clone. Configuration comes from process environment variables; `.env.example` is a reference and is not automatically loaded.

## Review the workflow

1. Requester creates a draft with 1-20 lines, units, quantities and estimated unit prices. Saving does not submit it.
2. Submit freezes the revision. The approver approves the exact submitted content or returns it with feedback.
3. Requester can edit full draft/returned details. Editing an approved request before ordering clears approval and creates a new revision. A PO freezes further editing.
4. Purchasing records supplier quotations with agreed unit prices and lead times. Comparison shows total price and budget fit. Selecting a supplier requires a rationale.
5. Issue one PO from a quotation belonging to the current approved revision. Agreed prices and supplier details are copied into the PO; estimates remain separate. Open its printable view to print or save PDF.
6. Receiver records inspected, accepted quantities. Partial receipts leave the remainder outstanding. Each delivery shows its line quantities. The request completes only when every ordered line is fully accepted.
7. Inspect submitted snapshots and activity history. Stale form versions conflict. An exact retried operation returns the original result instead of creating another write.

A detailed recording plan is in [the demo script](docs/demo-script.md).

## Quotation document input

Purchasing can choose **Upload quotation** on an approved request.

- **Local PDF text parser:** works without a provider. It reads explicit `Supplier:`, `Reference:`, `Lead days:` and `Item: description | quantity | unit | integer price` labels. It is explicitly labeled as parsing, not AI/OCR. Two synthetic PDFs and an AI image fixture are in [docs/samples](docs/samples/).
- **Optional Gemini AI:** set `GEMINI_API_KEY` and `AI_MODEL` in the server environment. The backend uses Google's Interactions API with PDF/image input, structured output and `store=false`. The upload form asks for explicit consent before sending a document to Google Gemini. No API call is made in local mode.
- **Review:** source, method, extracted values and evidence are shown before any quotation is created. The user selects the supplier, maps lines, verifies currency/prices/lead time, then confirms saving. Server validation still applies.
- **Failure:** timeout, refusal, incomplete/invalid output or missing configuration leaves manual entry available. The extractor cannot approve, select suppliers or issue orders.

Uploads are limited to 5 MB, PDFs to 5 unencrypted pages, images to 12 megapixels; images are re-encoded. Files use generated names outside static assets. Downloads check request access. Six uploads per user per 15 minutes limit repeated extraction.

Live AI extraction needs configured credentials and provider capacity. The [synthetic PNG and PDF fixtures](docs/samples/README.md) were verified with Gemini; accuracy across arbitrary supplier documents has not been measured. The regression suite validates request shape, schema handling, consent and failure behavior with mocks. Do not present local-parser results as measured model accuracy.

To enable Gemini locally, stop the running app and launch from a local PowerShell terminal:

```powershell
.\tools\start-ai.ps1 -Model 'gemini-3.8-flash'
```

The helper prompts for a key without echoing it, passes it only through the server process environment, and restores the terminal environment on exit. It checks the configured model with a small synthetic text request; no document is sent by that check. Invalid model/key access stops startup. Temporary HTTP 429/503 responses allow startup with a warning and local/manual input available. HTTP 503 is retried once. It never substitutes another model silently.

The helper reuses `DATABASE_URL` if set and never migrates or seeds a database. `-Port 5001 -DatabaseUrl 'sqlite:///instance/gemini-qa.sqlite' -Reload` runs an already initialized isolated demo with code reload and no debugger. Omit `-Reload` to serve through Waitress. `AI_MODEL` is configurable; confirm model access in the account. See Google's [Interactions API reference](https://ai.google.dev/api/interactions-api-v1) and [structured output guide](https://ai.google.dev/gemini-api/docs/structured-output). Do not paste keys into chat, frontend code, `VITE_` variables or Git. Documents are sent only after submitting AI mode with transfer consent.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check procurement tests run.py migrations
.\.venv\Scripts\python.exe -m ruff format --check procurement tests run.py migrations
.\.venv\Scripts\python.exe -m mypy --config-file pyproject.toml
.\.venv\Scripts\python.exe -m pytest tests/test_v4.py -q
```

For PostgreSQL regression, set `TEST_DATABASE_URL` to a dedicated database whose name ends in `_test`. Each test creates and removes its own generated schema; never point it at a business database. SQLite tests use isolated files under ignored `tmp/tests-v4`.

Browser regression changes data. Start a **separate disposable seeded app** in a new PowerShell terminal from the repository root. Use an unused database filename; seeding refuses to overwrite an existing populated database.

```powershell
$env:DATABASE_URL = 'sqlite:///instance/browser-demo.sqlite'
$env:PORT = '5002'
.\.venv\Scripts\python.exe run.py migrate
.\.venv\Scripts\python.exe run.py seed-demo
.\.venv\Scripts\python.exe run.py serve
```

Leave that server running. In another terminal from the repository root:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
$env:E2E_BASE_URL = 'http://127.0.0.1:5002'
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py --tracing retain-on-failure --screenshot only-on-failure
```

Without `E2E_BASE_URL`, browser tests skip. GitHub Actions config runs formatting, typing, SQLite/PostgreSQL regression and browser flows; remote CI results require publishing the repository.

## Source and required deliverables

- [BPMN PDF](docs/procurement-bpmn.pdf) and [editable draw.io diagram](docs/procurement-bpmn.drawio)
- [Excel WBS](docs/procurement-wbs.xlsx)
- [Scope, ERD and requirement mapping](docs/scope.md)
- [Architecture decisions](docs/decisions.md) and [debugging evidence](docs/debugging.md)

```text
procurement/
  __init__.py       Composition, configuration, CSRF and response headers
  auth.py           Session login/logout and login throttling
  web.py            HTTP routes and read-view assembly
  presentation.py   Public view-data serialization and React bootstrap
  inputs.py         Immutable typed request input and form validation
  workflow.py       Request revisions, approvals, search and summaries
  purchasing.py     Supplier/quotation records and itemized PO creation
  receiving.py      Accepted delivery quantities and completion
  operations.py     Role checks, locking, versions and retry protection
  documents.py      Protected upload and document review routes
  extraction.py     Local PDF parser and optional schema-validated AI
  models.py         SQLAlchemy records and constraints
  db.py             Engine/session lifecycle and migration entrypoint
migrations/         Reviewed versioned Alembic changes
frontend/src/       Feature modules, shared shadcn UI and typed transport
tests/              Domain, HTTP, migration, concurrency and browser checks
docs/               Required deliverables and review evidence
```

The v4 brief does not require Procurement chat/mobile. Warehouse management and payment remain excluded. Other explicit boundaries: one organization, four fixture roles, one approval stage, whole quantities and whole IDR, one supplier/PO per request, no tax or discounts, no supplier email sending or supplier portal. See scope for details.

## Existing v1 data and deployment

Stop application writers and back up the database before `migrate`. Only the recognized v1 table set is adopted automatically. Earlier agreed PO totals and accepted quantities are preserved. Since v1 did not record agreed line prices, migrated PO lines show **Not recorded** rather than invented prices. A submitted legacy snapshot is labeled as reconstructed. Destructive downgrades are disabled.

For deployment, use HTTPS, a managed random `SECRET_KEY`, `DEPLOYMENT=1` and `COOKIE_SECURE=1`. Replace demo identities, protect demo access, add account provisioning, trusted-proxy/IP rate limits, backups and document malware scanning appropriate to the environment. `.env.example` documents settings; the application does not auto-load it.

The exported BPMN PDF, editable draw.io source and Excel WBS are included. `tools/build_bpmn.py` and `tools/build_sample_quotations.py` use the Python development dependencies. The Excel WBS can be reviewed and edited directly in Excel.

All deliverables stay in this one repository. The confidential assessment PDFs and real supplier files are not copied into source control. No remote repository, public deployment or demo video has been published by this work.
