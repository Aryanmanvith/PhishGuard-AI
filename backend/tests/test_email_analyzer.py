"""Email analysis: wording rules, link extraction and sender consistency."""
from app.services.email_analyzer import MAX_LINKS_ANALYZED, analyze_email

PHISH_BODY = (
    "Dear customer,\n\nYour account will be suspended within 24 hours. Verify your account and confirm "
    "your password immediately: "
    '<a href="http://evil-login.top/x">https://paypal.com/secure</a>\n'
)


def ids(result):
    return {i.id for i in result.indicators if i.points > 0}


def test_ordinary_email_scores_low():
    r = analyze_email("Hi team, lunch at 1pm tomorrow? Notes: https://www.wikipedia.org", sender="Bob <bob@company.com>")
    assert r.risk_category == "low"
    assert "credential_request" not in ids(r) and "urgency" not in ids(r)


def test_phishing_email_is_high_with_explanations():
    r = analyze_email(PHISH_BODY, sender="PayPal Support <help@random-mail.biz>", reply_to="x@other.xyz")
    assert r.risk_category == "high" and r.risk_score >= 50
    assert {"urgency", "credential_request", "link_text_mismatch", "display_name_spoofing", "reply_to_mismatch"} <= ids(r)
    assert all(i.explanation and i.evidence for i in r.indicators)


def test_links_are_extracted_and_analyzed_statically():
    r = analyze_email("See http://192.168.1.5/login and https://example.com/page.")
    hosts = {link["host"] for link in r.details["links"]}
    assert hosts == {"192.168.1.5", "example.com"}
    assert "suspicious_links" in ids(r)


def test_sender_checks_skipped_without_sender():
    r = analyze_email("Please verify your account and enter your password now.")
    assert r.details["sender"]["provided"] is False
    assert any("No sender was supplied" in lim for lim in r.limitations)


def test_sender_with_matching_domain_is_not_penalised():
    r = analyze_email("Meeting notes: https://company.com/notes", sender="Bob <bob@company.com>")
    assert "links_not_matching_sender" not in ids(r)


def test_raw_body_and_subject_are_not_stored():
    secret = "my-very-private-sentence-12345"
    r = analyze_email(f"{secret}. Verify your account and enter your password.", subject="Private subject line")
    dumped = r.model_dump_json()
    assert secret not in dumped and "Private subject line" not in dumped


def test_link_count_is_capped():
    body = " ".join(f"https://site{i}.example.com/" for i in range(MAX_LINKS_ANALYZED + 5))
    r = analyze_email(body)
    assert len(r.details["links"]) == MAX_LINKS_ANALYZED
    assert any("Only the first" in lim for lim in r.limitations)


def test_malformed_sender_is_handled():
    r = analyze_email("hello there", sender="not an address")
    assert "sender_unparseable" in {i.id for i in r.indicators}
