"""Postgres backing store, used when a connection URL is configured.

Serverless hosts give each function a read-only filesystem apart from /tmp, so the
SQLite file cannot outlive a cold start. Setting PHISHGUARD_DATABASE_URL (or the
DATABASE_URL / POSTGRES_URL that Vercel's Postgres integrations provide) switches the
app to Postgres instead. Local development keeps using SQLite and needs no driver.

The connection returned here deliberately mimics sqlite3.Connection so repository.py
keeps one set of queries: it rewrites `?` placeholders to `%s`, maps SQLite's implicit
`rowid` onto a real column, and returns dict-like rows. Only the few constructs this
app actually uses are supported; this is not a general-purpose SQL translator.
"""
from __future__ import annotations

import re
from typing import Any, Iterator

# `seq` replaces SQLite's implicit rowid as the insertion-order tiebreaker in ORDER BY.
SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    seq             BIGSERIAL,
    id              TEXT PRIMARY KEY,
    input_type      TEXT NOT NULL CHECK (input_type IN ('url', 'email')),
    input_summary   TEXT NOT NULL,
    risk_score      INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_category   TEXT NOT NULL CHECK (risk_category IN ('low', 'suspicious', 'high')),
    ml_score        DOUBLE PRECISION,
    indicators_json TEXT NOT NULL,
    result_json     TEXT NOT NULL,
    is_demo         SMALLINT NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scans_created  ON scans (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_category ON scans (risk_category);
"""

_PLACEHOLDER = re.compile(r"\?")
_ROWID = re.compile(r"\browid\b")


def translate(sql: str) -> str:
    """SQLite SQL -> Postgres SQL for the dialect differences this app relies on."""
    return _PLACEHOLDER.sub("%s", _ROWID.sub("seq", sql))


class _Cursor:
    """Wraps a psycopg cursor so callers can chain .fetchone() / .fetchall() as sqlite3 allows."""

    def __init__(self, cur: Any) -> None:
        self._cur = cur

    def fetchone(self) -> Any:
        return self._cur.fetchone()

    def fetchall(self) -> list[Any]:
        return self._cur.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount


class PostgresConnection:
    """The subset of sqlite3.Connection that repository.py uses."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Any = ()) -> _Cursor:
        cur = self._conn.cursor()
        cur.execute(translate(sql), tuple(params) if params else None)
        return _Cursor(cur)

    def executescript(self, sql: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(sql)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def open_connection(url: str) -> PostgresConnection:
    """Connect with dict-like rows so `row["column"]` works exactly as under sqlite3.Row."""
    import psycopg
    from psycopg.rows import dict_row

    return PostgresConnection(psycopg.connect(url, row_factory=dict_row, connect_timeout=10))


def errors() -> tuple[type[BaseException], ...]:
    """Driver error types, imported lazily so SQLite-only installs need no psycopg."""
    try:
        import psycopg

        return (psycopg.Error,)
    except ImportError:  # pragma: no cover - only hit if the driver is missing
        return ()
