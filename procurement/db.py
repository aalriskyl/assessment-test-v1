from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from flask import Flask, current_app, g
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry


def init_app(app: Flask) -> None:
    url = app.config["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    schema = app.config.get("DATABASE_SCHEMA")
    connect_args = {}
    if schema:
        if not re.fullmatch(r"test_[a-z0-9]+", schema) or not app.config.get("TESTING"):
            raise RuntimeError("Isolated schemas are reserved for generated test schemas.")
        connect_args["options"] = f"-c search_path={schema}"
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection: sqlite3.Connection, record: ConnectionPoolEntry) -> None:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")

    app.extensions["engine"] = engine

    @app.teardown_appcontext
    def close_session(error: BaseException | None) -> None:
        database = g.pop("database", None)
        if database is not None:
            database.close()


def get_engine() -> Engine:
    return current_app.extensions["engine"]


def get_session() -> Session:
    if "database" not in g:
        g.database = Session(get_engine(), expire_on_commit=False)
    return g.database


@contextmanager
def transaction() -> Iterator[Session]:
    """Independent write session: auth and rendering never extend a write transaction."""
    with Session(get_engine(), expire_on_commit=False) as database:
        try:
            if database.bind is not None and database.bind.dialect.name == "sqlite":
                database.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield database
            database.commit()
        except BaseException:
            database.rollback()
            raise


def migrate() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    with get_engine().connect() as connection:
        config.attributes["connection"] = connection
        sqlite = connection.dialect.name == "sqlite"
        try:
            if sqlite:
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
            tables = set(inspect(connection).get_table_names())
            if "requests" in tables and "alembic_version" not in tables:
                expected = {
                    "users",
                    "suppliers",
                    "requests",
                    "request_items",
                    "purchase_orders",
                    "receipts",
                    "receipt_items",
                    "audit_events",
                    "login_attempts",
                }
                if not expected <= tables or "revision" in {
                    c["name"] for c in inspect(connection).get_columns("requests")
                }:
                    raise RuntimeError(
                        "Unrecognized legacy schema. Back up and inspect before migration."
                    )
                command.stamp(config, "0001")
                connection.commit()
            if sqlite:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            command.upgrade(config, "head")
            if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Migration failed foreign-key verification.")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            if sqlite:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def healthcheck() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
