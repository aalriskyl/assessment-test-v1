CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK(role IN ('requester','approver','purchasing','receiver')),
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    contact TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('low','normal','high')),
    needed_by TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft','submitted','rejected','approved','ordered','partial','received','cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS request_items (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id),
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10000),
    unit_price INTEGER NOT NULL CHECK(unit_price BETWEEN 1 AND 100000000000),
    received_quantity INTEGER NOT NULL DEFAULT 0 CHECK(received_quantity >= 0 AND received_quantity <= quantity)
);
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL UNIQUE REFERENCES requests(id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    quotation_reference TEXT NOT NULL,
    total INTEGER NOT NULL CHECK(total > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    delivery_reference TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_id, delivery_reference)
);
CREATE TABLE IF NOT EXISTS receipt_items (
    receipt_id INTEGER NOT NULL REFERENCES receipts(id),
    item_id INTEGER NOT NULL REFERENCES request_items(id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    PRIMARY KEY(receipt_id, item_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id),
    actor_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_requests_owner ON requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
CREATE INDEX IF NOT EXISTS idx_items_request ON request_items(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_events(request_id);
CREATE INDEX IF NOT EXISTS idx_login_email ON login_attempts(email);
