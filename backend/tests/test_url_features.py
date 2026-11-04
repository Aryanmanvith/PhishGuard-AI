"""Parsing, validation and feature extraction. No network, no database."""
import pytest

from app.services.url_features import (
    FEATURE_NAMES,
    InvalidURLError,
    compute_signals,
    extract_vector,
    parse_url,
    redact_url,
    split_host,
)


def sig(url: str):
    return compute_signals(parse_url(url))


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "example.com",  # no scheme
        "javascript:alert(1)",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "data:text/html,hello",
        "http://",
        "http://exa mple.com",  # space
        "http://example.com/\x00",  # control character
        "http://[::1",  # malformed IPv6
        "http://example.com:99999/",  # port out of range
        "http://-bad-.example.com",
        "http://exa$mple.com",
        "https://" + "a" * 3000 + ".com",  # too long
    ],
)
def test_invalid_urls_are_rejected(bad):
    with pytest.raises(InvalidURLError):
        parse_url(bad)


def test_plain_https_url_has_no_flags():
    s = sig("https://www.example.com/index.html")
    assert s.uses_https and not s.is_ip and not s.has_credentials and not s.has_punycode
    assert s.registered_domain == "example.com"
    assert s.subdomain_labels == ["www"]
    assert s.keywords == []


def test_ipv4_hostname():
    s = sig("http://192.168.0.1/login")
    assert s.is_ip and not s.is_obfuscated_ip


def test_ipv6_hostname_and_port():
    s = sig("http://[::1]:8080/")
    assert s.is_ip and s.port == 8080 and s.nonstandard_port


@pytest.mark.parametrize("url", ["http://3232235777/", "http://0xC0A80001/", "http://0177.0.0.1/"])
def test_obfuscated_ip_forms(url):
    s = sig(url)
    assert s.is_obfuscated_ip and not s.is_ip


def test_embedded_credentials():
    assert parse_url("https://user:pw@example.com/").username == "user"
    assert sig("https://user:pw@example.com/").has_credentials


def test_at_sign_trick_uses_last_at_as_host():
    s = sig("http://paypal.com@evil-site.top/update")
    assert s.has_credentials and s.host == "evil-site.top"


def test_punycode_and_mixed_script():
    assert sig("http://xn--pple-43d.com/").has_punycode
    mixed = sig("http://аpple.com/")  # Cyrillic 'a' + Latin 'pple'
    assert mixed.has_punycode and mixed.mixed_script


@pytest.mark.parametrize("url,expected", [
    ("http://example.com:8080/", True),
    ("http://example.com:80/", False),
    ("https://example.com:443/", False),
    ("https://example.com/", False),
])
def test_nonstandard_port(url, expected):
    assert sig(url).nonstandard_port is expected


def test_shortener_detected():
    assert sig("https://bit.ly/abc123").is_shortener
    assert not sig("https://example.com/abc123").is_shortener


def test_keywords_and_brand_mismatch():
    s = sig("http://paypal.com.secure-login.example.xyz/verify")
    assert {"secure", "login", "verify"} <= set(s.keywords)
    assert s.brand == "paypal"
    assert s.suspicious_tld


def test_legit_brand_domain_is_not_flagged():
    assert sig("https://www.paypal.com/signin").brand is None
    assert sig("https://accounts.google.com/login").brand is None


def test_embedded_url_and_dangerous_extension():
    assert sig("https://example.com/redirect?url=http://other.example/").embedded_url
    assert sig("https://example.com/files/setup.exe").dangerous_extension == ".exe"


def test_split_host_handles_two_part_suffix():
    assert split_host("shop.example.co.uk") == (["shop"], "example.co.uk")
    assert split_host("a.b.example.com") == (["a", "b"], "example.com")
    assert split_host("example.com") == ([], "example.com")


def test_redact_url_hides_password_and_truncates():
    out = redact_url("http://alice:s3cret@example.com/")
    assert "s3cret" not in out and "***" in out
    assert len(redact_url("http://example.com/" + "a" * 2000, max_len=100)) == 100


def test_vector_matches_feature_names_and_is_numeric():
    _parsed, _signals, vec = extract_vector("https://www.example.com/a/b?x=1&y=2")
    assert list(vec.keys()) == FEATURE_NAMES
    assert all(isinstance(v, float) for v in vec.values())
    assert vec["path_depth"] == 2.0 and vec["query_param_count"] == 2.0
