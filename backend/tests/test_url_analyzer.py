"""Rule-based URL analysis: scoring, explanations and the 'never touch the network' guarantee."""
import socket

import pytest

from app.services.ml_service import MLService
from app.services.url_analyzer import analyze_url
from app.services.url_features import InvalidURLError


def ids(result):
    return {i.id for i in result.indicators if i.points > 0}


def test_normal_urls_score_low():
    for url in ("https://www.wikipedia.org/wiki/Phishing", "https://docs.python.org/3/library/os.html"):
        r = analyze_url(url)
        assert r.risk_category == "low" and r.risk_score == 0
        assert ids(r) == set()


def test_login_keyword_alone_is_only_a_weak_signal():
    r = analyze_url("https://github.com/login")
    assert r.risk_category == "low" and ids(r) == {"suspicious_keywords"}


def test_ip_based_url_is_flagged():
    r = analyze_url("http://192.168.1.10:8080/login.php")
    assert "ip_hostname" in ids(r) and "unusual_port" in ids(r)
    assert r.risk_category in ("suspicious", "high")


def test_embedded_credentials_flagged_with_evidence():
    r = analyze_url("http://paypal.com@evil-site.top/update")
    assert "embedded_credentials" in ids(r)
    cred = next(i for i in r.indicators if i.id == "embedded_credentials")
    assert "evil-site.top" in cred.evidence and cred.explanation


def test_password_is_redacted_in_stored_summary():
    r = analyze_url("https://user:hunter2@bank-example.com/")
    assert "hunter2" not in r.input_summary and "hunter2" not in r.model_dump_json()


def test_https_does_not_make_a_url_safe():
    r = analyze_url("https://paypal.com.secure-login.example.xyz/verify")
    assert r.risk_category == "high"
    https_note = next(i for i in r.indicators if i.id == "https_note")
    assert https_note.points == 0 and https_note.severity == "info"
    assert "NOT make the URL safe" in https_note.explanation


def test_shortener_punycode_and_download_indicators():
    assert "url_shortener" in ids(analyze_url("https://bit.ly/abc"))
    assert "punycode" in ids(analyze_url("https://xn--pple-43d.com/"))
    assert "dangerous_extension" in ids(analyze_url("https://example.com/setup.exe"))


def test_score_is_capped_at_100():
    r = analyze_url("http://user:pw@192.168.1.1:8080/a//b/login/verify/secure/update.exe?u=http://x.example/" + "a" * 100)
    assert 0 <= r.risk_score <= 100


def test_result_has_required_fields_and_honest_wording():
    r = analyze_url("https://example.com/")
    assert r.analyzed_at.endswith("Z") and r.scan_id
    assert r.confidence.level in ("limited", "moderate")
    text = " ".join(r.limitations).lower()
    assert "never opened" in text and "not a probability" in text and "does not mean" in text


@pytest.mark.parametrize("bad", ["", "example.com", "javascript:alert(1)", "ftp://x.com", "http://"])
def test_invalid_input_raises(bad):
    with pytest.raises(InvalidURLError):
        analyze_url(bad)


def test_analysis_never_uses_the_network(monkeypatch):
    """Safety guarantee: analysing URLs must not open sockets or resolve DNS."""

    def boom(*_a, **_k):
        raise AssertionError("network access attempted during static analysis")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    for url in (
        "https://example.com/",
        "http://192.168.1.1/login",
        "https://bit.ly/x",
        "http://evil-login-verify.top/redirect?u=http://other.example",
    ):
        analyze_url(url)


def test_without_ml_service_no_ml_fields():
    r = analyze_url("https://example.com/")
    assert r.ml is None and r.comparison is None


def test_missing_model_degrades_gracefully(tmp_path):
    r = analyze_url("http://paypal.com.secure-login.example.xyz/verify", MLService(tmp_path / "nothing"))
    assert r.ml is not None and r.ml.available is False
    assert r.comparison.status == "unavailable"
    assert r.risk_category == "high"  # rule-based result is unaffected
