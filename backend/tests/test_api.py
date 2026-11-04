"""HTTP API tests (need fastapi + httpx; skipped automatically if they are not installed)."""
import json

import pytest

pytest.importorskip("fastapi.testclient")

from app.core.config import get_settings  # noqa: E402


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database_ok"] is True
    assert body["static_analysis_only"] is True
    assert body["model_available"] is False  # tests run with an empty model folder


def test_analyze_url_success(client):
    r = client.post("/api/analyze/url", json={"url": "https://www.example.com/"})
    assert r.status_code == 200
    body = r.json()
    assert body["input_type"] == "url" and body["risk_category"] == "low"
    assert 0 <= body["risk_score"] <= 100 and body["limitations"]
    assert body["ml"]["available"] is False


def test_analyze_url_flags_phishing_like_url(client):
    r = client.post("/api/analyze/url", json={"url": "http://paypal.com.secure-login.example.xyz/verify"})
    assert r.status_code == 200 and r.json()["risk_category"] == "high"


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://example.com/x", "not a url", "example.com"])
def test_invalid_urls_return_422_with_error_envelope(client, bad):
    r = client.post("/api/analyze/url", json={"url": bad})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "invalid_url" and err["message"]


def test_validation_errors(client):
    assert client.post("/api/analyze/url", json={}).status_code == 422
    assert client.post("/api/analyze/url", json={"url": ""}).json()["error"]["code"] == "validation_error"
    assert client.post("/api/analyze/url", json={"url": "https://a.com", "extra": 1}).status_code == 422
    assert client.post("/api/analyze/url", json={"url": "https://a.com/" + "x" * 3000}).status_code == 422
    assert client.post("/api/analyze/email", json={"body": "x" * 20_001}).status_code == 422


def test_analyze_email(client):
    r = client.post(
        "/api/analyze/email",
        json={
            "body": "Dear customer, verify your account and enter your password within 24 hours: http://192.168.1.5/login",
            "sender": "PayPal <x@mail.example.top>",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["input_type"] == "email" and body["risk_category"] in ("suspicious", "high")


def test_history_detail_and_404(client):
    first = client.post("/api/analyze/url", json={"url": "https://example.com/"}).json()
    client.post("/api/analyze/url", json={"url": "http://192.168.1.10/login"})

    listing = client.get("/api/scans").json()
    assert listing["total"] == 2 and len(listing["items"]) == 2
    assert client.get("/api/scans", params={"category": "low"}).json()["total"] == 1
    assert client.get("/api/scans", params={"limit": 1}).json()["items"].__len__() == 1
    assert client.get("/api/scans", params={"limit": 0}).status_code == 422
    assert client.get("/api/scans", params={"category": "bogus"}).status_code == 422

    detail = client.get(f"/api/scans/{first['scan_id']}")
    assert detail.status_code == 200 and detail.json()["scan_id"] == first["scan_id"]
    assert client.get("/api/scans/" + "0" * 32).status_code == 404
    assert client.get("/api/scans/not-a-valid-id").status_code == 422


def test_clear_history_requires_confirmation(client):
    client.post("/api/analyze/url", json={"url": "https://example.com/"})
    assert client.delete("/api/scans").status_code == 400
    assert client.get("/api/scans").json()["total"] == 1
    r = client.delete("/api/scans", params={"confirm": "true"})
    assert r.status_code == 200 and r.json()["deleted"] == 1
    assert client.get("/api/scans").json()["total"] == 0


def test_stats(client):
    client.post("/api/analyze/url", json={"url": "https://example.com/"})
    stats = client.get("/api/stats").json()
    assert stats["total_scans"] == 1 and stats["by_category"]["low"] == 1
    assert len(stats["last_14_days"]) == 14


def test_json_report_download(client):
    scan = client.post("/api/analyze/url", json={"url": "http://192.168.1.10/login"}).json()
    r = client.get(f"/api/scans/{scan['scan_id']}/report.json")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    report = json.loads(r.text)
    assert report["scan"]["scan_id"] == scan["scan_id"] and report["disclaimer"]


def test_csv_history_download(client):
    client.post("/api/analyze/url", json={"url": "https://example.com/"})
    r = client.get("/api/reports/history.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert "scan_id" in r.text.splitlines()[0]


def test_model_endpoint_reports_unavailable_model(client):
    body = client.get("/api/model").json()
    assert body["available"] is False and body["reason"]


def test_demo_seed_is_labelled_and_idempotent(client):
    first = client.post("/api/demo/seed").json()
    assert first["inserted"] > 0
    assert client.post("/api/demo/seed").json()["inserted"] == 0
    items = client.get("/api/scans", params={"limit": 100}).json()["items"]
    assert items and all(i["is_demo"] for i in items)
    assert client.delete("/api/scans", params={"confirm": "true", "demo_only": "true"}).json()["deleted"] == first["inserted"]


def test_oversized_body_rejected(client):
    r = client.post("/api/analyze/email", content=b"x" * 200_000, headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "payload_too_large"


def test_rate_limit(isolated_env, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("PHISHGUARD_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        codes = [c.get("/api/health").status_code for _ in range(6)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]


def test_cors_allows_only_configured_origins(client):
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_security_headers_and_error_envelope(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
    missing = client.get("/api/does-not-exist")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
