"""Rule-based URL analysis (the explainable half of PhishGuard).

Each rule looks at one property of the URL string and, if it fires, produces an
`Indicator` with: points, the evidence we saw, and a plain-language reason.
The heuristic score is the capped SUM of those points. It is a transparent
weighted checklist, not a probability.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.risk import ML_FLAG_THRESHOLD, SUSPICIOUS_THRESHOLD, categorize
from app.schemas.scan import Comparison, Confidence, Indicator, MLResult, ScanResult
from app.services.ml_service import MLService
from app.services.url_features import UrlSignals, extract_vector, redact_url

URL_LIMITATIONS = [
    "Static analysis only: the URL was never opened, resolved or followed, so page content, redirects and server behaviour were not examined.",
    "The score is a weighted checklist of URL characteristics (0-100). It is not a probability and is not calibrated.",
    "A low score does not mean a URL is safe. New, compromised or well-crafted phishing pages can look clean.",
    "HTTPS only means the connection is encrypted. Attackers use HTTPS too.",
    "Domain age, WHOIS, TLS certificates and blocklists are not checked (offline by design).",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ind(id_: str, title: str, severity: str, points: int, evidence: str, explanation: str) -> Indicator:
    return Indicator(
        id=id_, title=title, severity=severity, points=points, evidence=evidence, explanation=explanation
    )


def evaluate_signals(s: UrlSignals) -> list[Indicator]:
    """Turn raw URL signals into explainable indicators."""
    out: list[Indicator] = []

    if s.has_credentials:
        out.append(_ind(
            "embedded_credentials", "Embedded credentials in URL", "high", 30, f"Host: {s.host}",
            "Everything before the '@' is a username, not the site. Attackers write "
            "'https://trusted-name@evil.com' so the real destination hides after the '@'.",
        ))

    if s.is_obfuscated_ip:
        out.append(_ind(
            "obfuscated_ip", "Obfuscated IP-address hostname", "high", 30, f"Host: {s.host}",
            "The host is written as a number (decimal, hex or octal) that browsers convert to an IP address. "
            "This is a classic way to hide where a link really goes.",
        ))
    elif s.is_ip:
        out.append(_ind(
            "ip_hostname", "IP address instead of a domain name", "high", 25, f"Host: {s.host}",
            "Legitimate services almost always use a domain name. A raw IP address is common in "
            "throwaway phishing infrastructure and malware downloads.",
        ))

    if s.mixed_script:
        out.append(_ind(
            "homograph", "Mixed-script hostname (look-alike characters)", "high", 30, f"Host: {s.host}",
            "The hostname mixes Latin letters with Cyrillic or Greek ones that look identical. "
            "This is used to imitate well-known domains.",
        ))
    elif s.has_punycode:
        out.append(_ind(
            "punycode", "Punycode / non-ASCII hostname", "medium", 20, f"Host: {s.host}",
            "Internationalised domains are encoded as 'xn--'. They are legitimate in many languages, "
            "but can also be used to imitate a familiar brand with look-alike characters.",
        ))

    if s.brand:
        out.append(_ind(
            "brand_impersonation", "Brand name on an unrelated domain", "high", 25,
            f"'{s.brand}' appears in the URL but the registered domain is {s.registered_domain}",
            f"The URL mentions '{s.brand}' but does not belong to that brand's official domains. "
            "Phishing pages commonly put a well-known name in the subdomain or path.",
        ))

    if s.is_shortener:
        out.append(_ind(
            "url_shortener", "URL-shortening service", "medium", 15, f"Shortener: {s.registered_domain}",
            "A shortened link hides its destination. PhishGuard does not follow redirects, "
            "so the real target is unknown.",
        ))

    if s.dangerous_extension:
        out.append(_ind(
            "dangerous_extension", "Link points to a downloadable program file", "high", 15,
            f"Path ends with {s.dangerous_extension}",
            "Links that directly download executables or scripts are a common malware delivery method.",
        ))

    if s.nonstandard_port:
        out.append(_ind(
            "unusual_port", "Unusual port number", "medium", 10, f"Port: {s.port}",
            "Normal websites use ports 80 (http) or 443 (https). Other ports are uncommon for public pages "
            "and often seen on temporary servers.",
        ))

    if s.embedded_url:
        out.append(_ind(
            "embedded_url", "Another URL embedded inside this URL", "medium", 8,
            "A second 'http(s)://' appears in the path or query",
            "Redirect-style links ('?url=http://...') can bounce a visitor from a trusted-looking site to another one.",
        ))

    n_sub = len(s.subdomain_labels)
    if n_sub >= 4:
        out.append(_ind(
            "many_subdomains", "Very deep subdomain chain", "medium", 10, f"{n_sub} subdomain labels in {s.host}",
            "Long chains of subdomains push the real domain out of sight on small screens and can imitate trusted names.",
        ))
    elif n_sub == 3:
        out.append(_ind(
            "many_subdomains", "Deep subdomain chain", "low", 5, f"{n_sub} subdomain labels in {s.host}",
            "Several subdomain levels can be used to make a hostname look familiar at a glance.",
        ))

    if s.hyphen_count_host >= 3:
        out.append(_ind(
            "many_hyphens", "Many hyphens in hostname", "low", 8, f"{s.hyphen_count_host} hyphens in {s.host}",
            "Names like 'secure-login-update-account' are typical of throwaway phishing domains.",
        ))

    if s.digit_count_host >= 4:
        out.append(_ind(
            "digits_in_host", "Many digits in hostname", "low", 5, f"{s.digit_count_host} digits in {s.host}",
            "Heavy use of digits in a domain name is more common in generated or disposable domains.",
        ))

    if len(s.keywords) >= 3:
        pts, sev = 14, "medium"
    elif len(s.keywords) == 2:
        pts, sev = 8, "low"
    elif len(s.keywords) == 1:
        pts, sev = 4, "low"
    else:
        pts, sev = 0, "low"
    if pts:
        out.append(_ind(
            "suspicious_keywords", "Credential-related keywords", sev, pts, "Found: " + ", ".join(s.keywords),
            "Words such as 'login', 'verify' or 'secure' are used to make a page look official. "
            "Legitimate sites use them too, so this is only a weak signal.",
        ))

    if s.suspicious_tld:
        out.append(_ind(
            "suspicious_tld", "Frequently abused top-level domain", "low", 8, f"TLD: .{s.tld}",
            "Some TLDs are over-represented in abuse reports because they are cheap or free. "
            "Many legitimate sites use them too.",
        ))

    if s.percent_count >= 3:
        out.append(_ind(
            "percent_encoding", "Heavy percent-encoding", "low", 6, f"{s.percent_count} encoded characters",
            "Excessive %XX encoding can be used to hide the real content of a link.",
        ))

    if s.double_slash_in_path:
        out.append(_ind(
            "double_slash", "Double slash inside the path", "low", 5, "'//' found after the hostname",
            "A '//' in the path can indicate a redirect trick or a sloppily built link.",
        ))

    if s.host_entropy >= 3.6 and len(s.registered_domain.split(".")[0]) >= 12:
        out.append(_ind(
            "random_domain", "Random-looking domain name", "low", 6,
            f"Domain label entropy {s.host_entropy:.2f} bits/char",
            "Machine-generated domains tend to look random. This is a weak statistical signal.",
        ))

    if s.url_length > 120:
        out.append(_ind(
            "very_long_url", "Very long URL", "medium", 10, f"{s.url_length} characters",
            "Very long URLs can bury the real hostname or hide extra parameters.",
        ))
    elif s.url_length > 75:
        out.append(_ind(
            "long_url", "Long URL", "low", 5, f"{s.url_length} characters",
            "Longer URLs give attackers more room to disguise their destination.",
        ))

    if not s.uses_https:
        out.append(_ind(
            "no_https", "Not using HTTPS", "low", 10, "Scheme is http://",
            "Traffic is unencrypted, so anything typed could be read in transit. Modern legitimate sites almost always use HTTPS.",
        ))
    else:
        out.append(_ind(
            "https_note", "HTTPS in use (informational)", "info", 0, "Scheme is https://",
            "HTTPS encrypts the connection but says nothing about who runs the site. "
            "A large share of phishing sites also use HTTPS. It does NOT make the URL safe.",
        ))

    return out


def build_comparison(rule_score: int, ml: MLResult) -> Comparison:
    if not ml.available or ml.score is None:
        return Comparison(
            status="unavailable",
            summary="The machine-learning model is not available, so only the rule-based analysis is shown.",
        )
    rules_flag = rule_score >= SUSPICIOUS_THRESHOLD
    ml_flag = ml.score >= ML_FLAG_THRESHOLD
    if rules_flag and ml_flag:
        return Comparison(status="agree", summary="Both the rules and the model see phishing-like characteristics.")
    if not rules_flag and not ml_flag:
        return Comparison(
            status="agree",
            summary="Neither the rules nor the model see strong phishing-like characteristics. This is not proof of safety.",
        )
    if rules_flag:
        return Comparison(
            status="disagree",
            summary="The rules flag this URL but the model does not. The model only learned patterns from its training data, "
                    "so review the rule indicators manually.",
        )
    return Comparison(
        status="disagree",
        summary="The model leans phishing-like but the rules found few indicators. The model may be reacting to a "
                "combination of features; check its top contributing features.",
    )


def build_confidence(indicators: list[Indicator], comparison: Comparison | None) -> Confidence:
    strong = [i for i in indicators if i.severity in ("medium", "high")]
    agree = comparison is not None and comparison.status == "agree"
    if len(strong) >= 3 or (len(strong) >= 2 and agree):
        return Confidence(
            level="moderate",
            note="Several independent indicators point the same way. Still a static estimate, not a verdict.",
        )
    return Confidence(
        level="limited",
        note="Static URL analysis has limited visibility. Treat the result as a hint and verify through a trusted channel.",
    )


def analyze_url(raw_url: str, ml_service: MLService | None = None, *, is_demo: bool = False) -> ScanResult:
    """Analyze one URL string. Raises InvalidURLError for unsupported input. Never touches the network."""
    parsed, signals, vector = extract_vector(raw_url)

    indicators = evaluate_signals(signals)
    score = min(100, sum(i.points for i in indicators))
    category = categorize(score)

    ml_result: MLResult | None = None
    comparison: Comparison | None = None
    if ml_service is not None:
        ml_result = ml_service.predict(vector)
        comparison = build_comparison(score, ml_result)

    limitations = list(URL_LIMITATIONS)
    if ml_result is not None and ml_result.available:
        limitations.append(
            "The ML model only sees URL text features and inherits the biases of its training data."
        )

    return ScanResult(
        scan_id=uuid.uuid4().hex,
        input_type="url",
        input_summary=redact_url(parsed.raw),
        risk_score=score,
        risk_category=category,
        indicators=sorted(indicators, key=lambda i: (-i.points, i.title)),
        ml=ml_result,
        comparison=comparison,
        confidence=build_confidence(indicators, comparison),
        limitations=limitations,
        details={
            "host": signals.host,
            "registered_domain": signals.registered_domain,
            "scheme": parsed.scheme,
            "features": vector,
        },
        analyzed_at=utc_now_iso(),
        is_demo=is_demo,
    )
