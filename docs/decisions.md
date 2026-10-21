# Architecture decisions

## One application with explicit operation boundaries

Flask Blueprints handle authentication, view routes and document upload. Typed request input is parsed at the HTTP boundary. Request lifecycle, purchasing and receiving functions enforce permissions and own complete database transactions. They do not accept Flask request objects. SQLAlchemy models describe relational constraints. This keeps decisions testable without introducing generic repositories or an event bus.

## React organized by feature

React/TypeScript uses feature folders for requests, purchasing, receiving and authentication. Shared visual primitives live in `components/ui` (shadcn), domain-neutral form components in `components`, formatting and HTTP transport in `lib`, and screen composition/navigation in `app`. Components own temporary form state; the Python operations own persisted business state. No duplicate client workflow engine or global business store is introduced.

Flask owns the URLs and returns explicit public view DTOs when `Accept: application/json` is requested. A normal deep link renders a small HTML shell with escaped bootstrap JSON and Vite manifest assets. The shared client handles same-origin navigation, CSRF-protected forms, redirects, pending submissions, stale responses and network failures. User and document serializers exclude credentials, storage paths and extraction internals. The Python-only quick start uses the included bundle; CI rebuilds from the locked frontend source.

## Local display time, stable stored time

Database event timestamps stay UTC for ordering and interoperability. One frontend formatter displays them in Asia/Jakarta with a WIB label, independent of the browser timezone. Date-only delivery requirements are not timezone-shifted. Tests cover crossing a UTC day boundary and morning/noon conversion.

## PostgreSQL and SQLite are both supported

PostgreSQL is used for the current shared preview; SQLite is the zero-service local default. The same regression suite runs against SQLite and isolated PostgreSQL test schemas. PostgreSQL locks the owning request with `FOR UPDATE`; SQLite begins an immediate write transaction. Actor locks serialize operation-token checks. Multi-record operations acquire actor then request locks in that order. External model calls never run inside write transactions.

SQLite migration adopts only the recognized v1 table set, then applies Alembic revisions. SQLite batch migration runs with foreign-key enforcement temporarily disabled on its dedicated migration connection and verifies foreign keys before commit. Run migrations while application writers are stopped and keep a verified backup. Unfamiliar schemas are rejected; downgrades that would erase procurement history are disabled.

## Approval belongs to a submitted revision

Submitting freezes a JSON snapshot of the exact request. An owner may edit a draft, returned request or approved request before a PO exists. Editing a submitted revision creates a new revision and clears approval. Previous requested lines, snapshots and quotation lines remain available for traceability. A PO requires the current approved revision and a quotation belonging to that revision.

## Issued prices are independent of estimates

Requested lines contain estimates. Each quotation snapshots requested item descriptions, units, quantities and supplier prices. A PO copies those agreed prices and the supplier identity/contact. Receiving is bounded by PO line quantities. One supplier and one PO per request keep this version focused. Multiple deliveries are supported.

Legacy orders recorded only an agreed total. Their migration preserves the original total and accepted quantities, leaves agreed line prices unknown, and visibly labels the limitation. It does not fabricate a historical price allocation or approval decision.

## Retries are operations, not additional purchases

Forms carry an operation token. The database stores actor, token, payload fingerprint and resulting request in the same transaction as the business write. Exact retries return the original result. Reusing a token with changed input fails with a conflict. Unique PO/request, quotation/reference and delivery/reference constraints provide additional protection. Expected version checks reject stale forms from another tab or user.

## Extraction has no purchasing authority

Document extraction produces an untrusted preview. Purchasing explicitly selects a supplier, maps extracted lines to requested items and reviews prices before saving a quotation. The server requires confirmation and applies normal validation. The extractor has no business-operation tools.

The local parser handles explicitly labeled PDF text and is labeled as a parser, not AI/OCR. Optional Google Gemini Interactions integration supports PDF/images and schema validation, with a fixed provider endpoint, timeout, bounded output, `store=false` and explicit document-transfer consent in the UI. It requires `GEMINI_API_KEY` and `AI_MODEL`; there is no hard-coded model or credential. Live provider behavior must be verified with configured credentials before claiming AI accuracy.

## Scope limits are deliberate

No inventory ledger, payment, supplier portal, vendor email sending, multi-supplier split PO, tax calculation, fractional quantities, approval thresholds or public hosting. Account roles are seeded reference accounts; user administration and session revocation are future work. Demo credentials are documented in README and omitted from the login UI.
