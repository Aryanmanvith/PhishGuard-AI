"""Orchestration layer: analyze -> save -> return.

API routes call these functions so the HTTP layer stays thin and the logic can be
unit-tested without starting a web server.
"""
from __future__ import annotations

from app.core.errors import AppError, NotFoundError
from app.database import repository
from app.schemas.scan import ScanResult
from app.services.demo_data import DEMO_EMAILS, DEMO_URLS, demo_timestamp
from app.services.email_analyzer import analyze_email
from app.services.ml_service import get_ml_service
from app.services.url_analyzer import analyze_url
from app.services.url_features import InvalidURLError


def scan_url(url: str) -> ScanResult:
    try:
        result = analyze_url(url, get_ml_service())
    except InvalidURLError as exc:
        raise AppError(str(exc), code="invalid_url", status_code=422) from exc
    repository.insert_scan(result)
    return result


def scan_email(body: str, sender: str | None, reply_to: str | None, subject: str | None) -> ScanResult:
    result = analyze_email(body, sender=sender, reply_to=reply_to, subject=subject)
    repository.insert_scan(result)
    return result


def fetch_scan(scan_id: str) -> ScanResult:
    scan = repository.get_scan(scan_id)
    if scan is None:
        raise NotFoundError("Scan not found.")
    return scan


def seed_demo_data() -> int:
    """Insert demo scans once. Returns how many were added (0 if demo data already exists)."""
    if repository.count_demo_scans() > 0:
        return 0
    inserted = 0
    index = 0
    for url in DEMO_URLS:
        result = analyze_url(url, get_ml_service(), is_demo=True)
        result.analyzed_at = demo_timestamp(index)
        repository.insert_scan(result)
        inserted += 1
        index += 1
    for sample in DEMO_EMAILS:
        result = analyze_email(
            sample["body"], sender=sample.get("sender"), reply_to=sample.get("reply_to"),
            subject=sample.get("subject"), is_demo=True,
        )
        result.analyzed_at = demo_timestamp(index)
        repository.insert_scan(result)
        inserted += 1
        index += 1
    return inserted
