"""JSON scan reports and CSV history export."""
import csv
import io

from app.services.report_service import HISTORY_COLUMNS, _safe_cell, build_history_csv, build_scan_report
from app.services.url_analyzer import analyze_url


def test_scan_report_contains_evidence_score_and_limitations():
    scan = analyze_url("http://paypal.com.secure-login.example.xyz/verify")
    report = build_scan_report(scan)
    assert report["scan"]["risk_score"] == scan.risk_score
    assert report["scan"]["indicators"][0]["evidence"]
    assert report["scan"]["analyzed_at"] and report["scan"]["limitations"]
    assert "not a probability" in report["disclaimer"]
    assert report["recommendations"]


def test_history_csv_structure():
    scans = [analyze_url("https://example.com/"), analyze_url("http://192.168.1.1/login")]
    text = build_history_csv(scans)
    assert text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    assert rows[0] == HISTORY_COLUMNS and len(rows) == 3
    assert rows[2][HISTORY_COLUMNS.index("risk_category")] in ("suspicious", "high")


def test_csv_formula_injection_is_neutralised():
    assert _safe_cell("=HYPERLINK(\"http://x\")").startswith("'=")
    assert _safe_cell("+1+1").startswith("'+")
    assert _safe_cell("@SUM(A1)").startswith("'@")
    assert _safe_cell("normal") == "normal"
