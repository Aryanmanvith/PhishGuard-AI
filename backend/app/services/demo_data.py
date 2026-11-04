"""Clearly-labelled DEMO samples used to populate an empty dashboard.

These are synthetic inputs built on reserved example domains (RFC 2606 /
RFC 5737). They are run through the REAL analyzers, but every stored row is
flagged is_demo=True so the UI marks them as demo data, never as real detections.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

DEMO_URLS = [
    "https://www.wikipedia.org/wiki/Phishing",
    "https://docs.python.org/3/library/urllib.parse.html",
    "https://github.com/login",
    "https://example.com/products/shoes?color=blue&size=42",
    "https://bit.ly/demo-link",
    "https://example.com/download/invoice-scan.exe",
    "http://192.0.2.15:8080/login.php",
    "https://user:password@bank-demo.example.com/",
    "http://xn--pple-43d.example.com/",
    "http://paypal.com.secure-login.example-demo.xyz/verify/account",
    "http://secure-update-account-verify.example-demo.top/signin?next=http://evil.example/",
    "http://paypal.com@login-check.example-demo.top/update",
]

DEMO_EMAILS = [
    {
        "sender": "Alice <alice@example.org>",
        "body": "Hi team,\n\nThe quarterly planning meeting moved to Thursday 3pm. Agenda: https://example.org/wiki/q3-planning\n\nThanks,\nAlice",
    },
    {
        "sender": "PayPal Support <help@account-alerts.example-demo.top>",
        "reply_to": "recover@mailbox.example-demo.xyz",
        "subject": "Final notice: account suspended",
        "body": (
            "Dear customer,\n\nUnusual activity was detected. Your account will be suspended within 24 hours. "
            "Verify your account and confirm your password immediately: "
            "<a href=\"http://paypal.com.secure-login.example-demo.xyz/verify\">https://www.paypal.com/signin</a>\n"
        ),
    },
]


def demo_timestamp(index: int) -> str:
    """Spread demo rows over the last ~10 days so the dashboard charts have something to show."""
    when = datetime.now(timezone.utc) - timedelta(days=index % 10, hours=index % 7)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")
