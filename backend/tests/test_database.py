"""SQLite persistence: insert, read, filter, stats, clear, and constraint enforcement."""
import sqlite3

import pytest

from app.database import repository
from app.database.db import connect
from app.services.email_analyzer import analyze_email
from app.services.url_analyzer import analyze_url


def test_insert_and_get_roundtrip(isolated_env):
    result = analyze_url("http://192.168.1.10:8080/login.php")
    repository.insert_scan(result)
    loaded = repository.get_scan(result.scan_id)
    assert loaded is not None
    assert loaded.risk_score == result.risk_score
    assert [i.id for i in loaded.indicators] == [i.id for i in result.indicators]
    assert repository.get_scan("f" * 32) is None


def test_list_filters_and_pagination(isolated_env):
    for url in ("https://example.com/", "http://192.168.1.10/login", "https://www.wikipedia.org/"):
        repository.insert_scan(analyze_url(url))
    repository.insert_scan(analyze_email("Verify your account and enter your password immediately."))

    items, total = repository.list_scans()
    assert total == 4 and len(items) == 4
    _items, url_total = repository.list_scans(input_type="url")
    assert url_total == 3
    _items, email_total = repository.list_scans(input_type="email")
    assert email_total == 1
    page, total = repository.list_scans(limit=2, offset=2)
    assert len(page) == 2 and total == 4
    low_items, _ = repository.list_scans(category="low")
    assert all(i.risk_category == "low" for i in low_items)


def test_stats_counts(isolated_env):
    repository.insert_scan(analyze_url("https://example.com/"))
    repository.insert_scan(analyze_url("http://paypal.com.secure-login.example.xyz/verify"))
    stats = repository.get_stats()
    assert stats.total_scans == 2
    assert stats.by_category["low"] == 1 and stats.by_category["high"] == 1
    assert stats.by_input_type == {"url": 2, "email": 0}
    assert len(stats.last_14_days) == 14 and sum(d.total for d in stats.last_14_days) == 2
    assert stats.top_indicators


def test_clear_all_and_demo_only(isolated_env):
    real = analyze_url("https://example.com/")
    demo = analyze_url("https://example.com/demo", is_demo=True)
    repository.insert_scan(real)
    repository.insert_scan(demo)
    assert repository.clear_scans(demo_only=True) == 1
    assert repository.get_scan(real.scan_id) is not None
    assert repository.clear_scans() == 1
    assert repository.list_scans()[1] == 0


def test_check_constraints_reject_bad_rows(isolated_env):
    with pytest.raises(sqlite3.IntegrityError):
        with connect() as conn:
            conn.execute(
                "INSERT INTO scans VALUES ('x','url','s',150,'high',NULL,'[]','{}',0,'2026-01-01T00:00:00Z')"
            )


def test_sql_injection_in_filters_is_inert(isolated_env):
    repository.insert_scan(analyze_url("https://example.com/"))
    items, total = repository.list_scans(category="low' OR '1'='1")
    assert total == 0 and items == []
    assert repository.get_scan("x' OR '1'='1") is None
    assert repository.list_scans()[1] == 1  # table intact
