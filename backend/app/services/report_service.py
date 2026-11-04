"""Builds downloadable reports (JSON for one scan, CSV for the whole history)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from app.schemas.scan import ScanResult

REPORT_DISCLAIMER = (
    "This report is the output of a static, heuristic analysis. The risk score is a weighted checklist, "
    "not a probability, and a low score does not guarantee safety. Verify suspicious messages through an "
    "official channel and report phishing to your organisation's security team."
)

METHODOLOGY = [
    "URLs are analyzed as text only. They are never opened, resolved or followed.",
    "Each rule that fires adds points; the heuristic score is the sum capped at 100.",
    "Categories: low (<20), suspicious (20-49), high (50+).",
    "The ML model, when present, looks only at lexical URL features and is shown separately for comparison.",
]

RECOMMENDATIONS = {
    "high": [
        "Do not click the link or open attachments.",
        "Do not enter credentials or payment details.",
        "Report the message to your IT/security team or mail provider.",
        "If you already interacted with it, change affected passwords and enable multi-factor authentication.",
    ],
    "suspicious": [
        "Do not click the link directly; type the official address in your browser or use a saved bookmark.",
        "Verify the request through a separate trusted channel (phone number from the official website).",
    ],
    "low": [
        "Few warning signs were found, but a low score is not a guarantee of safety.",
        "Stay cautious if the message asks for sensitive information or creates urgency.",
    ],
}


def build_scan_report(scan: ScanResult) -> dict:
    return {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": "PhishGuard AI",
        "analysis_type": "static (nothing was opened, fetched or followed)",
        "scan": scan.model_dump(),
        "recommendations": RECOMMENDATIONS[scan.risk_category],
        "methodology": METHODOLOGY,
        "disclaimer": REPORT_DISCLAIMER,
    }


def _safe_cell(value: object) -> str:
    """Neutralise spreadsheet formula injection: cells starting with = + - @ are prefixed with a quote."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


HISTORY_COLUMNS = [
    "scan_id", "analyzed_at_utc", "input_type", "input_summary", "risk_score", "risk_category",
    "ml_score_not_a_probability", "demo_data", "indicators", "limitations",
]


def build_history_csv(scans: list[ScanResult]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(HISTORY_COLUMNS)
    short_limit = "Static heuristic analysis; score is not a probability; low score does not guarantee safety."
    for s in scans:
        ml_score = s.ml.score if s.ml is not None and s.ml.available else ""
        indicators = " | ".join(
            f"{i.title} (+{i.points}): {i.evidence}" for i in s.indicators if i.points > 0
        )
        writer.writerow([
            _safe_cell(v)
            for v in (
                s.scan_id, s.analyzed_at, s.input_type, s.input_summary, s.risk_score, s.risk_category,
                ml_score, "yes" if s.is_demo else "no", indicators, short_limit,
            )
        ])
    return "﻿" + buf.getvalue()  # BOM so Excel on Windows reads UTF-8 correctly
