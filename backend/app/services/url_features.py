"""URL parsing and feature extraction (STATIC ONLY).

Nothing in this file touches the network. We only look at the characters of the
URL string. That is the core safety rule of the project: a submitted URL is
treated as inert text and is never fetched, resolved, or followed.

Two consumers share this file:
  * the rule engine (url_analyzer.py) uses the rich `UrlSignals` object, and
  * the ML pipeline uses `signals_to_vector()` -> a fixed list of numbers.
Sharing one extractor guarantees training and prediction see identical features.
"""
from __future__ import annotations

import ipaddress
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = {"http", "https"}


class InvalidURLError(ValueError):
    """The input is not a URL we are willing to analyze."""


# --------------------------------------------------------------- reference data

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorturl.at", "tiny.cc", "rb.gy", "lnkd.in",
    "bl.ink", "s.id", "t.ly", "v.gd", "shorte.st",
}

# Words that often appear in credential-harvesting URLs. Many are also common on
# legitimate sites ("account", "support"), so each one only adds a few points.
SUSPICIOUS_KEYWORDS = (
    "login", "signin", "sign-in", "verify", "verification", "account", "update",
    "secure", "security", "banking", "password", "passwd", "confirm", "wallet",
    "suspend", "unlock", "invoice", "payment", "billing", "recover", "validate",
    "authenticate", "helpdesk",
)

# TLDs that public abuse reports list as over-represented in phishing. This is a
# weak signal: plenty of legitimate sites use them too.
SUSPICIOUS_TLDS = {
    "zip", "mov", "top", "xyz", "click", "country", "gq", "tk", "ml", "cf", "ga",
    "work", "link", "rest", "cam", "icu", "buzz", "loan", "monster",
}

# Public-suffix handling without a dependency: a small list of common two-part
# suffixes. Real code would use the Public Suffix List (documented limitation).
MULTI_PART_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.in",
    "net.in", "org.in", "ac.in", "gov.in", "edu.in", "co.jp", "com.br", "com.cn",
    "co.nz", "co.za", "com.mx", "com.sg", "com.tr",
}

# Brand token -> registered domains that legitimately belong to that brand.
BRANDS: dict[str, set[str]] = {
    "paypal": {"paypal.com"},
    "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "office.com", "microsoftonline.com", "outlook.com"},
    "google": {"google.com", "gmail.com", "youtube.com", "googleapis.com"},
    "amazon": {"amazon.com", "amazon.in", "amazon.co.uk", "amazonaws.com"},
    "facebook": {"facebook.com", "fb.com"},
    "netflix": {"netflix.com"},
    "instagram": {"instagram.com"},
    "whatsapp": {"whatsapp.com"},
    "linkedin": {"linkedin.com"},
    "dropbox": {"dropbox.com"},
    "docusign": {"docusign.com", "docusign.net"},
    "fedex": {"fedex.com"},
    "coinbase": {"coinbase.com"},
    "binance": {"binance.com"},
    "paytm": {"paytm.com"},
    "hdfcbank": {"hdfcbank.com"},
    "icicibank": {"icicibank.com"},
    "chase": {"chase.com"},
    "wellsfargo": {"wellsfargo.com"},
    "bankofamerica": {"bankofamerica.com"},
}

DANGEROUS_EXTENSIONS = (
    ".exe", ".scr", ".bat", ".cmd", ".msi", ".apk", ".jar", ".vbs", ".iso", ".lnk", ".js",
)

_OBFUSCATED_IP = re.compile(r"^(0x[0-9a-f]+|[0-9]+)(\.(0x[0-9a-f]+|[0-9]+)){0,3}$")


# --------------------------------------------------------------------- parsing


@dataclass(frozen=True)
class ParsedURL:
    raw: str
    scheme: str
    host: str
    port: int | None
    has_userinfo: bool
    username: str | None
    path: str
    query: str
    fragment: str


def _valid_label(label: str) -> bool:
    if not 1 <= len(label) <= 63:
        return False
    if label.startswith("-") or label.endswith("-"):
        return False
    return all(ch.isalnum() or ch in "-_" for ch in label)


def parse_url(raw: str) -> ParsedURL:
    """Validate and split a URL string. Raises InvalidURLError with a user-safe message."""
    if not isinstance(raw, str):
        raise InvalidURLError("URL must be text.")
    url = raw.strip()
    if not url:
        raise InvalidURLError("URL is empty.")
    if len(url) > MAX_URL_LENGTH:
        raise InvalidURLError(f"URL is longer than {MAX_URL_LENGTH} characters.")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise InvalidURLError("URL contains spaces or control characters.")

    try:
        parts = urlsplit(url)
    except ValueError as exc:  # e.g. malformed IPv6 brackets
        raise InvalidURLError("URL could not be parsed (malformed structure).") from exc

    scheme = parts.scheme.lower()
    if not scheme:
        raise InvalidURLError("URL must start with http:// or https://")
    if scheme not in ALLOWED_SCHEMES:
        shown = scheme[:20]
        raise InvalidURLError(f"Scheme '{shown}' is not supported. Only http and https URLs are analyzed.")

    try:
        port = parts.port
    except ValueError as exc:
        raise InvalidURLError("URL has an invalid port number.") from exc

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise InvalidURLError("URL has no hostname.")
    if len(host) > 253:
        raise InvalidURLError("Hostname is too long.")

    if not (_is_ip(host) or _OBFUSCATED_IP.match(host)):
        if not all(_valid_label(label) for label in host.split(".")):
            raise InvalidURLError("Hostname contains invalid characters or empty labels.")

    return ParsedURL(
        raw=url,
        scheme=scheme,
        host=host,
        port=port,
        has_userinfo="@" in parts.netloc,
        username=parts.username,
        path=parts.path,
        query=parts.query,
        fragment=parts.fragment,
    )


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def redact_url(url: str, max_len: int = 500) -> str:
    """Hide a password if one is embedded (scheme://user:SECRET@host) and cap the length."""
    cleaned = re.sub(r"(://[^/@:\s]*:)[^/@\s]*@", r"\1***@", url)
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1] + "…"


# ------------------------------------------------------------- domain helpers


def split_host(host: str) -> tuple[list[str], str]:
    """Return (subdomain_labels, registered_domain) using a simple suffix heuristic."""
    if _is_ip(host) or _OBFUSCATED_IP.match(host):
        return [], host
    labels = host.split(".")
    if len(labels) <= 2:
        return [], host
    suffix2 = ".".join(labels[-2:])
    keep = 3 if suffix2 in MULTI_PART_SUFFIXES else 2
    return labels[:-keep], ".".join(labels[-keep:])


def registered_domain(host: str) -> str:
    return split_host(host)[1]


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _find_brand(host_tokens_source: str, path: str, reg_domain: str) -> str | None:
    tokens = re.split(r"[^a-z0-9]+", f"{host_tokens_source} {path}".lower())
    for brand, legit_domains in BRANDS.items():
        if reg_domain in legit_domains:
            continue
        for tok in tokens:
            if tok == brand or (len(brand) >= 6 and brand in tok):
                return brand
    return None


def find_brand(text: str, reg_domain: str) -> str | None:
    """Public helper: does `text` (e.g. an email display name) mention a brand that
    does not own `reg_domain`?"""
    return _find_brand(text, "", reg_domain)


def _mixed_script(host: str) -> bool:
    scripts = set()
    for ch in host:
        if ch.isalpha() and ord(ch) > 127:
            scripts.add(unicodedata.name(ch, "UNKNOWN").split(" ")[0])
        elif ch.isalpha():
            scripts.add("LATIN")
    return len(scripts) > 1 and any(s in scripts for s in ("CYRILLIC", "GREEK"))


# -------------------------------------------------------------------- signals


@dataclass
class UrlSignals:
    url_length: int
    host: str
    host_length: int
    path_length: int
    query_length: int
    host_dot_count: int
    subdomain_labels: list[str]
    registered_domain: str
    tld: str
    hyphen_count_host: int
    digit_count_host: int
    digit_ratio_url: float
    special_char_count: int
    path_depth: int
    query_param_count: int
    is_ip: bool
    is_obfuscated_ip: bool
    uses_https: bool
    has_at_symbol: bool
    has_credentials: bool
    has_punycode: bool
    mixed_script: bool
    port: int | None
    nonstandard_port: bool
    is_shortener: bool
    keywords: list[str] = field(default_factory=list)
    brand: str | None = None
    suspicious_tld: bool = False
    percent_count: int = 0
    host_entropy: float = 0.0
    double_slash_in_path: bool = False
    max_label_length: int = 0
    embedded_url: bool = False
    dangerous_extension: str | None = None


def compute_signals(p: ParsedURL) -> UrlSignals:
    host = p.host
    is_ip = _is_ip(host)
    is_obf = (not is_ip) and bool(_OBFUSCATED_IP.match(host))
    subs, reg = split_host(host)
    labels = host.split(".")
    tld = labels[-1] if len(labels) > 1 and not (is_ip or is_obf) else ""

    full_lower = p.raw.lower()
    search_space = f"{host}{p.path}?{p.query}".lower()
    keywords = [k for k in SUSPICIOUS_KEYWORDS if k in search_space]

    main_label = reg.split(".")[0] if reg else host
    punycode = any(lbl.startswith("xn--") for lbl in labels) or any(ord(c) > 127 for c in host)
    nonstandard = p.port is not None and p.port not in (80, 443)
    lower_path = p.path.lower()
    dangerous = next((ext for ext in DANGEROUS_EXTENSIONS if lower_path.endswith(ext)), None)
    digits_in_url = sum(c.isdigit() for c in p.raw)

    return UrlSignals(
        url_length=len(p.raw),
        host=host,
        host_length=len(host),
        path_length=len(p.path),
        query_length=len(p.query),
        host_dot_count=host.count("."),
        subdomain_labels=subs,
        registered_domain=reg,
        tld=tld,
        hyphen_count_host=host.replace("xn--", "").count("-"),
        digit_count_host=sum(c.isdigit() for c in host) if not (is_ip or is_obf) else 0,
        digit_ratio_url=round(digits_in_url / max(len(p.raw), 1), 4),
        special_char_count=sum(p.raw.count(c) for c in "@?&=_%~#"),
        path_depth=len([seg for seg in p.path.split("/") if seg]),
        query_param_count=len([q for q in p.query.split("&") if q]),
        is_ip=is_ip,
        is_obfuscated_ip=is_obf,
        uses_https=p.scheme == "https",
        has_at_symbol="@" in p.raw,
        has_credentials=p.has_userinfo,
        has_punycode=punycode,
        mixed_script=_mixed_script(host),
        port=p.port,
        nonstandard_port=nonstandard,
        is_shortener=host in SHORTENERS or reg in SHORTENERS,
        keywords=keywords,
        brand=None if (is_ip or is_obf) else _find_brand(host, p.path, reg),
        suspicious_tld=tld in SUSPICIOUS_TLDS,
        percent_count=len(re.findall(r"%[0-9a-fA-F]{2}", p.raw)),
        host_entropy=round(_shannon_entropy(main_label), 3) if not (is_ip or is_obf) else 0.0,
        double_slash_in_path="//" in p.path,
        max_label_length=max((len(lbl) for lbl in labels), default=0),
        embedded_url=("http://" in (p.path + p.query).lower() or "https://" in (p.path + p.query).lower()
                      or "http%3a" in full_lower or "https%3a" in full_lower),
        dangerous_extension=dangerous,
    )


# ------------------------------------------------------------------ ML vector

# Order matters: the trained model expects exactly this order.
FEATURE_LABELS: dict[str, str] = {
    "url_length": "URL length",
    "host_length": "Hostname length",
    "path_length": "Path length",
    "query_length": "Query string length",
    "host_dot_count": "Dots in hostname",
    "subdomain_count": "Number of subdomains",
    "hyphen_count_host": "Hyphens in hostname",
    "digit_count_host": "Digits in hostname",
    "digit_ratio_url": "Share of digits in URL",
    "special_char_count": "Special characters (@ ? & = _ % ~ #)",
    "path_depth": "Path depth",
    "query_param_count": "Query parameters",
    "has_ip_host": "IP-address hostname",
    "uses_https": "Uses HTTPS",
    "has_at_symbol": "Contains '@'",
    "has_credentials": "Embedded credentials",
    "has_punycode": "Punycode / non-ASCII host",
    "has_nonstandard_port": "Unusual port",
    "is_shortener": "URL shortener",
    "keyword_count": "Suspicious keywords",
    "brand_mismatch": "Brand name on unrelated domain",
    "suspicious_tld": "Frequently abused TLD",
    "percent_encoding_count": "Percent-encoded characters",
    "host_entropy": "Domain name randomness (entropy)",
    "double_slash_in_path": "'//' inside path",
    "max_label_length": "Longest hostname label",
    "embedded_url": "URL embedded in URL",
}
FEATURE_NAMES: list[str] = list(FEATURE_LABELS.keys())


def signals_to_vector(s: UrlSignals) -> dict[str, float]:
    return {
        "url_length": float(s.url_length),
        "host_length": float(s.host_length),
        "path_length": float(s.path_length),
        "query_length": float(s.query_length),
        "host_dot_count": float(s.host_dot_count),
        "subdomain_count": float(len(s.subdomain_labels)),
        "hyphen_count_host": float(s.hyphen_count_host),
        "digit_count_host": float(s.digit_count_host),
        "digit_ratio_url": float(s.digit_ratio_url),
        "special_char_count": float(s.special_char_count),
        "path_depth": float(s.path_depth),
        "query_param_count": float(s.query_param_count),
        "has_ip_host": float(s.is_ip or s.is_obfuscated_ip),
        "uses_https": float(s.uses_https),
        "has_at_symbol": float(s.has_at_symbol),
        "has_credentials": float(s.has_credentials),
        "has_punycode": float(s.has_punycode),
        "has_nonstandard_port": float(s.nonstandard_port),
        "is_shortener": float(s.is_shortener),
        "keyword_count": float(len(s.keywords)),
        "brand_mismatch": float(s.brand is not None),
        "suspicious_tld": float(s.suspicious_tld),
        "percent_encoding_count": float(s.percent_count),
        "host_entropy": float(s.host_entropy),
        "double_slash_in_path": float(s.double_slash_in_path),
        "max_label_length": float(s.max_label_length),
        "embedded_url": float(s.embedded_url),
    }


def extract_vector(raw_url: str) -> tuple[ParsedURL, UrlSignals, dict[str, float]]:
    parsed = parse_url(raw_url)
    signals = compute_signals(parsed)
    return parsed, signals, signals_to_vector(signals)
