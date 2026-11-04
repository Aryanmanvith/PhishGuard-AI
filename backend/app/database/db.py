"""Database connection helper and schema.

We use Python's built-in sqlite3 module directly (no ORM) so every query is
visible and easy to explain. All values are passed as parameters (`?`), never
formatted into SQL strings, which prevents SQL injection.

When settings.database_url is set the same queries run against Postgres instead, so
scan history survives on hosts with an ephemeral filesystem. An explicit `path`
argument always means SQLite, which is what the tests use.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.core.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id              TEXT PRIMARY KEY,
    input_type      TEXT NOT NULL CHECK (input_type IN ('url', 'email')),
    input_summary   TEXT NOT NULL,
    risk_score      INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_category   TEXT NOT NULL CHECK (risk_category IN ('low', 'suspicious', 'high')),
    ml_score        REAL,
    indicators_json TEXT NOT NULL,
    result_json     TEXT NOT NULL,
    is_demo         INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scans_created  ON scans (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_category ON scans (risk_category);
"""


def _db_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else get_settings().db_path


def _postgres_url(path: Path | str | None) -> str:
    """The configured Postgres URL, or "" when this call should use SQLite."""
    return "" if path is not None else get_settings().database_url


def init_db(path: Path | str | None = None) -> None:
    url = _postgres_url(path)
    if url:
        from app.database import postgres

        with connect(path) as conn:
            conn.executescript(postgres.SCHEMA)
        return
    p = _db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with connect(p) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[Any]:
    """Open a connection, commit on success, roll back on error, always close."""
    url = _postgres_url(path)
    if url:
        from app.database import postgres

        conn: Any = postgres.open_connection(url)
    else:
        conn = sqlite3.connect(str(_db_path(path)), timeout=10)
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_db(path: Path | str | None = None) -> bool:
    expected: tuple[type[BaseException], ...] = (sqlite3.Error,)
    if _postgres_url(path):
        from app.database import postgres

        expected += postgres.errors()
    try:
        with connect(path) as conn:
            conn.execute("SELECT 1 FROM scans LIMIT 1")
        return True
    except expected:
        return False
