"""Rule-based phishing analysis for pasted email text.

Privacy: everything runs locally. Nothing is sent to a third-party service, the
raw email body is never written to the database (only a short summary and the
indicators), and links found in the email are analyzed statically (never opened).
"""
from __future__ import annotations

import re
import uuid
from email.utils import parseaddr

from app.models.risk import SUSPICIOUS_THRESHOLD, categorize
from app.schemas.scan import Indicator, ScanResult
from app.services.url_analyzer import analyze_url, build_confidence, utc_now_iso
from app.services.url_features import InvalidURLError, find_brand, parse_url, redact_url, registered_domain

MAX_LINKS_ANALYZED = 20

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]{1,2048}", re.I)
ANCHOR_RE = re.compile(
    r"<a\s[^>]{0,500}?href\s*=\s*[\"']([^\"']{1,2048})[\"'][^>]{0,500}>([^<]{0,300})</a>", re.I
)
TAG_RE = re.compile(r"<[^>]{0,2000}>")
DOMAIN_IN_TEXT_RE = re.compile(r"(?:https?://)?((?:[a-z0-9-]{1,63}\.)+[a-z]{2,24})\b", re.I)
SENDER_ADDR_RE = re.compile(r"^[^@\s]{1,64}@([A-Za-z0-9.-]{1,253})$")

# (id, title, severity, explanation, [regex...], points by number of distinct matches (1, 2, 3+))
TEXT_RULES: list[tuple[str, str, str, str, list[str], tuple[int, int, int]]] = [
    (
        "urgency", "Urgency or pressure language", "medium",
        "Phishing messages push you to act before you think: deadlines, threats of closure, 'immediately'.",
        [
            r"\burgent(ly)?\b", r"\bimmediate(ly)?\b", r"\bact now\b", r"\bwithin \d{1,3} (hours?|days?)\b",
            r"\bfinal (notice|warning)\b", r"\blast (chance|warning)\b", r"\bexpires? (today|soon|in)\b",
            r"\b(account|access) (will be |has been |is )?(suspended|closed|locked|disabled|terminated|limited)\b",
        ],
        (8, 12, 15),
    ),
    (
        "credential_request", "Asks for passwords, codes or identity details", "high",
        "Legitimate organisations do not ask you to send passwords, one-time codes, PINs or card numbers by email.",
        [
            r"\b(enter|provide|confirm|verify|update|send|reply with|share)\b[^.\n]{0,40}\b"
            r"(password|passcode|credentials|username|pin|otp|one[- ]time (code|password)|security code|verification code)\b",
            r"\b(cvv|card number|social security|ssn|aadhaar|pan card|bank account number|routing number)\b",
            r"\bverify (your )?(account|identity|information)\b",
            r"\b(log ?in|sign ?in) (to|and) (verify|confirm|update|restore)\b",
        ],
        (25, 25, 25),
    ),
    (
        "payment_request", "Payment or money-transfer pressure", "medium",
        "Requests for wire transfers, gift cards, crypto or 'updated payment details' are common in fraud.",
        [
            r"\bwire transfer\b", r"\bgift cards?\b", r"\b(bitcoin|btc|crypto(currency)?|usdt)\b",
            r"\b(payment|invoice|transaction) (failed|declined|overdue|pending)\b",
            r"\bupdate (your )?(billing|payment) (details|information|method)\b",
            r"\bpay (immediately|now|today)\b",
        ],
        (15, 20, 20),
    ),
    (
        "threat", "Threats or consequences", "medium",
        "Scare tactics such as legal action or permanent closure are used to rush you.",
        [
            r"\blegal action\b", r"\bpermanently (closed|deleted|suspended)\b",
            r"\bwe will (suspend|close|terminate|delete)\b",
            r"\bunauthori[sz]ed (login|access|activity|transaction)\b",
        ],
        (10, 10, 10),
    ),
    (
        "reward_lure", "Prize, refund or reward lure", "medium",
        "Unexpected prizes, refunds or cashback are bait to get you to click or share details.",
        [
            r"\byou('ve| have) (won|been selected)\b", r"\bclaim your (prize|reward|refund)\b",
            r"\b(lottery|prize|reward|refund|cashback) (is )?(waiting|available|pending)\b",
        ],
        (10, 10, 10),
    ),
    (
        "attachment_lure", "Risky attachment or macro instructions", "medium",
        "Phishing often asks you to open an attachment or enable macros, which can install malware.",
        [
            r"\benable (macros|content|editing)\b", r"\b(open|see|view|download) the attach(ed|ment)\b",
            r"\b[\w-]{1,40}\.(exe|scr|vbs|iso|lnk|docm|xlsm)\b",
        ],
        (10, 10, 10),
    ),
    (
        "generic_greeting", "Generic greeting", "low",
        "Messages from companies that know you usually use your name rather than 'Dear customer'.",
        [r"\bdear (customer|user|member|client|account holder|valued (customer|user|member))\b"],
        (5, 5, 5),
    ),
]
_COMPILED = [(r[:5] + (r[5],), [re.compile(p, re.I) for p in r[4]]) for r in TEXT_RULES]

EMAIL_LIMITATIONS = [
    "Only the pasted text was analyzed. Email headers (SPF, DKIM, DMARC), attachments and message routing were not examined.",
    "Wording rules are pattern based: genuine emails can match them and carefully written phishing can avoid them.",
    "Links found in the email were analyzed as text only. They were never opened or followed.",
    "The score is a weighted checklist (0-100), not a probability. A low score does not mean the email is safe.",
    "Analysis runs locally. The raw email body is not stored; only a short summary and the indicators are saved.",
]


def _ind(id_: str, title: str, severity: str, points: int, evidence: str, explanation: str) -> Indicator:
    return Indicator(id=id_, title=title, severity=severity, points=points, evidence=evidence, explanation=explanation)


def _strip_html(body: str) -> str:
    return TAG_RE.sub(" ", body)


def _extract_links(body: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (unique URLs in order, [(anchor_text, href), ...])."""
    anchors = [(m.group(2).strip(), m.group(1).strip()) for m in ANCHOR_RE.finditer(body)]
    urls: list[str] = [href for _text, href in anchors]
    urls += [m.group(0).rstrip(".,;:!?") for m in URL_RE.finditer(body)]
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique, anchors


def _text_indicators(text: str) -> list[Indicator]:
    lowered = text.lower()
    out: list[Indicator] = []
    for (id_, title, sev, explanation, _patterns, tiers), regexes in _COMPILED:
        matches: list[str] = []
        for rx in regexes:
            for m in rx.finditer(lowered):
                phrase = " ".join(m.group(0).split())[:60]
                if phrase not in matches:
                    matches.append(phrase)
                if len(matches) >= 6:
                    break
        if not matches:
            continue
        points = tiers[0] if len(matches) == 1 else tiers[1] if len(matches) == 2 else tiers[2]
        out.append(_ind(id_, title, sev, points, "Phrases: " + "; ".join(f'"{m}"' for m in matches[:4]), explanation))
    return out


def _sender_indicators(sender: str | None, reply_to: str | None, link_domains: set[str]) -> tuple[list[Indicator], dict]:
    info: dict = {"provided": bool(sender), "domain": None, "parsed": False}
    out: list[Indicator] = []
    if not sender:
        return out, info

    display_name, addr = parseaddr(sender)
    m = SENDER_ADDR_RE.match(addr or "")
    if not m:
        out.append(_ind(
            "sender_unparseable", "Sender address could not be parsed", "low", 5, "Sender field is not a valid address",
            "A malformed or missing sender address is unusual for legitimate mail.",
        ))
        return out, info

    domain = m.group(1).lower().rstrip(".")
    reg = registered_domain(domain)
    info.update({"parsed": True, "domain": domain})

    brand = find_brand(display_name, reg) if display_name else None
    if brand:
        out.append(_ind(
            "display_name_spoofing", "Sender name mentions a brand but the domain is unrelated", "high", 25,
            f"Display name mentions '{brand}', sending domain is {reg}",
            "Attackers set the visible name to a trusted brand while sending from an unrelated address.",
        ))

    name_domain = DOMAIN_IN_TEXT_RE.search(display_name or "")
    if name_domain and registered_domain(name_domain.group(1).lower()) != reg:
        out.append(_ind(
            "display_name_domain_mismatch", "Display name shows a different domain than the real sender", "high", 20,
            f"Name shows {name_domain.group(1).lower()}, address uses {reg}",
            "A domain or address placed in the display name is meant to look like the real sender.",
        ))

    try:
        sender_result = analyze_url(f"https://{domain}")
        if sender_result.risk_score >= SUSPICIOUS_THRESHOLD:
            titles = ", ".join(i.title for i in sender_result.indicators if i.points > 0)[:120]
            out.append(_ind(
                "suspicious_sender_domain", "Sender domain looks suspicious", "medium",
                min(20, sender_result.risk_score // 2), f"{domain}: {titles}",
                "The sending domain shows the same warning signs we check in URLs.",
            ))
    except InvalidURLError:
        out.append(_ind(
            "sender_domain_invalid", "Sender domain looks malformed", "low", 5, domain,
            "The domain part of the sender address is not a normal hostname.",
        ))

    if reply_to:
        _name, reply_addr = parseaddr(reply_to)
        rm = SENDER_ADDR_RE.match(reply_addr or "")
        if rm and registered_domain(rm.group(1).lower()) != reg:
            out.append(_ind(
                "reply_to_mismatch", "Reply-To points to a different domain", "medium", 15,
                f"From {reg}, replies go to {registered_domain(rm.group(1).lower())}",
                "Replies are redirected somewhere other than the sender's own domain, a common scam technique.",
            ))

    if link_domains and reg not in link_domains:
        out.append(_ind(
            "links_not_matching_sender", "Links go to domains unrelated to the sender", "low", 5,
            "Link domains: " + ", ".join(sorted(link_domains))[:120],
            "Legitimate emails usually link to the sender's own domain. Marketing mail often does not, so this is a weak signal.",
        ))
    return out, info


def analyze_email(
    body: str,
    sender: str | None = None,
    reply_to: str | None = None,
    subject: str | None = None,
    *,
    is_demo: bool = False,
) -> ScanResult:
    plain = _strip_html(body)
    indicators = _text_indicators(f"{subject or ''}\n{plain}")

    urls, anchors = _extract_links(body)
    link_entries: list[dict] = []
    unparseable = 0
    for url in urls[:MAX_LINKS_ANALYZED]:
        try:
            res = analyze_url(url)
        except InvalidURLError:
            unparseable += 1
            continue
        link_entries.append({
            "url": redact_url(url, 300),
            "host": res.details["host"],
            "registered_domain": res.details["registered_domain"],
            "risk_score": res.risk_score,
            "risk_category": res.risk_category,
            "top_indicators": [i.title for i in res.indicators if i.points > 0][:3],
        })

    if link_entries:
        worst = max(link_entries, key=lambda e: e["risk_score"])
        if worst["risk_score"] >= SUSPICIOUS_THRESHOLD:
            indicators.append(_ind(
                "suspicious_links", "Message contains a risky link", "high" if worst["risk_score"] >= 50 else "medium",
                min(40, round(0.4 * worst["risk_score"])),
                f"{worst['host']} scored {worst['risk_score']}/100 ({', '.join(worst['top_indicators']) or 'see details'})",
                "A link inside the message shows URL-level warning signs. The link was not opened.",
            ))

    # Link text vs real destination (only possible when HTML anchors were pasted).
    for text, href in anchors[:MAX_LINKS_ANALYZED]:
        shown = DOMAIN_IN_TEXT_RE.search(text)
        if not shown:
            continue
        try:
            real = registered_domain(parse_url(href).host)
        except InvalidURLError:
            continue
        if registered_domain(shown.group(1).lower()) != real:
            indicators.append(_ind(
                "link_text_mismatch", "Link text shows a different site than the link target", "high", 25,
                f"Text shows {shown.group(1).lower()} but the link goes to {real}",
                "The visible text and the real destination differ, a hallmark of phishing links.",
            ))
            break

    link_domains = {e["registered_domain"] for e in link_entries}
    sender_inds, sender_info = _sender_indicators(sender, reply_to, link_domains)
    indicators += sender_inds

    score = min(100, sum(i.points for i in indicators))
    sender_part = sender_info["domain"] or ("unparseable sender" if sender else "sender not provided")
    summary = f"Email · {sender_part} · {len(link_entries)} link(s) · {len(body)} chars"

    limitations = list(EMAIL_LIMITATIONS)
    if not sender:
        limitations.append("No sender was supplied, so sender and domain consistency checks were skipped.")
    if unparseable:
        limitations.append(f"{unparseable} link(s) in the text could not be parsed as http(s) URLs and were skipped.")
    if len(urls) > MAX_LINKS_ANALYZED:
        limitations.append(f"Only the first {MAX_LINKS_ANALYZED} of {len(urls)} links were analyzed.")

    return ScanResult(
        scan_id=uuid.uuid4().hex,
        input_type="email",
        input_summary=summary,
        risk_score=score,
        risk_category=categorize(score),
        indicators=sorted(indicators, key=lambda i: (-i.points, i.title)),
        ml=None,
        comparison=None,
        confidence=build_confidence(indicators, None),
        limitations=limitations,
        details={
            "sender": {"domain": sender_info["domain"], "provided": sender_info["provided"]},
            "reply_to_checked": bool(reply_to),
            "links": link_entries,
            "character_count": len(body),
        },
        analyzed_at=utc_now_iso(),
        is_demo=is_demo,
    )
