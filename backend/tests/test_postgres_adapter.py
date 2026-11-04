"""Tests for the Postgres adapter's SQL translation and sqlite3-compatible surface.

These do not need a Postgres server. A fake driver backed by sqlite3 drives the real
repository functions through PostgresConnection, which checks the plumbing: placeholder
rewriting, rowid -> seq, chained fetchone()/fetchall(), rowcount, and dict-like rows.
Server-side dialect behaviour (BIGSERIAL, Decimal from AVG) still needs a real database.
"""
from __future__ import annotations

import re
import sqlite3

import pytest

from app.database import postgres
from app.database.postgres import PostgresConnection, translate


def test_translate_rewrites_placeholders_and_rowid():
    sql = "SELECT id FROM scans WHERE risk_category = ? ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?"
    out = translate(sql)
    assert "?" not in out
    assert out.count("%s") == 3
    assert "rowid" not in out and "seq DESC" in out


def test_translate_leaves_substrings_containing_rowid_alone():
    # \b guards against mangling a column that merely contains "rowid".
    assert "browrowid" in translate("SELECT browrowid FROM scans")


def test_postgres_schema_defines_seq_for_ordering():
    # repository.py orders by rowid; translate() maps it to seq, so seq must exist.
    assert "seq" in postgres.SCHEMA
    assert "BIGSERIAL" in postgres.SCHEMA


class _FakeCursor:
    """sqlite3 cursor presented the way psycopg's dict_row cursor behaves."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._cur = conn.cursor()

    def execute(self, sql: str, params=None):
        # Undo the Postgres placeholder so sqlite can run the translated statement.
        self._cur.execute(re.sub(r"%s", "?", sql), params or ())
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeDriverConnection:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self.committed = False

    def cursor(self):
        return _FakeCursor(self._conn)

    def commit(self):
        self.committed = True
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@pytest.fixture()
def pg(tmp_path):
    conn = PostgresConnection(_FakeDriverConnection(str(tmp_path / "t.db")))
    # seq stands in for the BIGSERIAL column the Postgres schema declares.
    conn.executescript(
        "CREATE TABLE scans (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, risk_category TEXT, is_demo INTEGER)"
    )
    yield conn
    conn.close()


def test_execute_translates_and_returns_dict_rows(pg):
    pg.execute("INSERT INTO scans (id, risk_category, is_demo) VALUES (?, ?, ?)", ("a", "high", 1))
    row = pg.execute("SELECT id, risk_category FROM scans WHERE id = ?", ("a",)).fetchone()
    assert row["id"] == "a" and row["risk_category"] == "high"


def test_execute_without_params_is_accepted(pg):
    assert pg.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"] == 0


def test_rowcount_survives_the_wrapper(pg):
    for i in range(3):
        pg.execute("INSERT INTO scans (id, risk_category, is_demo) VALUES (?, ?, ?)", (str(i), "low", 1))
    assert pg.execute("DELETE FROM scans WHERE is_demo = 1").rowcount == 3


def test_rowid_ordering_uses_the_seq_column(pg):
    for i in ("x", "y", "z"):
        pg.execute("INSERT INTO scans (id, risk_category, is_demo) VALUES (?, ?, 0)", (i, "low"))
    rows = pg.execute("SELECT id FROM scans ORDER BY rowid DESC").fetchall()
    assert [r["id"] for r in rows] == ["z", "y", "x"]


def test_commit_and_rollback_reach_the_driver(pg):
    pg.commit()
    assert pg._conn.committed is True
