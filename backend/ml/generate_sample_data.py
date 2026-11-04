"""Generate a small SYNTHETIC demo dataset (data/sample_urls.csv).

!! This is NOT real phishing data. !!
The URLs are invented from word lists using patterns that are commonly described
in phishing write-ups (IP hosts, brand names on unrelated domains, hyphen-heavy
hostnames, ...) plus plenty of "hard" look-alike cases. It exists so the project
runs offline and the ML pipeline can be demonstrated end-to-end. Any metrics
computed from it say nothing about real-world accuracy. For real results, train
on a real dataset (see backend/data/README.md and docs/ML_NOTES.md).

Usage (from the backend folder):
    python -m ml.generate_sample_data
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

OUT_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "sample_urls.csv"

BENIGN_WORDS = [
    "maple", "river", "stone", "north", "bright", "cloud", "green", "delta", "orbit", "pixel", "harbor",
    "summit", "violet", "cedar", "atlas", "nova", "ember", "lotus", "quartz", "willow", "falcon", "meadow",
    "copper", "linen", "tundra", "aurora", "bamboo", "canyon", "dune", "echo",
]
BENIGN_SUFFIX = ["labs", "works", "hub", "soft", "media", "shop", "news", "tech", "bank", "learn", "health", "travel"]
BENIGN_TLDS = ["com", "org", "net", "io", "edu", "co.uk", "in", "dev"]
BENIGN_PATHS = [
    "", "/", "/about", "/contact", "/blog/2024/05/how-we-built-it", "/products/item-1234", "/docs/getting-started",
    "/news/article-slug", "/pricing", "/careers/open-roles", "/help/faq", "/search?q=widgets&page=2",
    "/account/settings", "/login", "/support/tickets", "/store/category/shoes?color=blue&size=42",
]

PHISH_WORDS = [
    "zenith", "pulse", "vertex", "mango", "lunar", "prism", "ripple", "cobalt", "ginger", "onyx", "jolt", "karma",
    "nimbus", "opal", "quill", "raven", "sable", "talon", "umber", "vortex",
]
PHISH_TLDS = ["xyz", "top", "tk", "ml", "cf", "ga", "click", "icu", "work", "link", "com", "net", "info"]
BRANDS = ["paypal", "microsoft", "apple", "amazon", "netflix", "google", "facebook", "dropbox", "linkedin"]
SECURE_WORDS = ["secure", "login", "verify", "account", "update", "signin", "confirm", "support", "billing"]
PHISH_PATHS = [
    "/verify", "/login.php", "/signin/confirm", "/account/update", "/secure/index.html", "/wp-includes/login/verify.php",
    "/auth/session?id={n}", "/confirm?token={n}", "/update-billing", "/webscr?cmd=_login", "/",
]


def _rand_id(rng: random.Random, n: int = 12) -> str:
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))


def benign_url(rng: random.Random) -> tuple[str, str]:
    domain = f"{rng.choice(BENIGN_WORDS)}{rng.choice(BENIGN_SUFFIX) if rng.random() < 0.6 else ''}"
    if rng.random() < 0.12:
        domain = f"{rng.choice(BENIGN_WORDS)}-{rng.choice(BENIGN_WORDS)}"
    host = f"{domain}.{rng.choice(BENIGN_TLDS)}"
    registered = host
    if rng.random() < 0.55:
        host = "www." + host
    elif rng.random() < 0.15:
        host = f"{rng.choice(['blog', 'app', 'docs', 'shop'])}.{host}"
    scheme = "https" if rng.random() < 0.93 else "http"
    port = ":8443" if rng.random() < 0.01 else ""
    path = rng.choice(BENIGN_PATHS)
    return f"{scheme}://{host}{port}{path}", registered


def phishing_url(rng: random.Random) -> tuple[str, str]:
    kind = rng.choices(
        ["ip", "brand_sub", "hyphen", "random", "at", "puny", "compromised", "compromised2", "short_like"],
        weights=[10, 18, 14, 10, 6, 5, 22, 10, 5],
    )[0]
    tld = rng.choice(PHISH_TLDS)
    scheme = "http" if rng.random() < 0.45 else "https"
    path = rng.choice(PHISH_PATHS).format(n=rng.randint(1000, 999999))

    if kind == "ip":
        ip = ".".join(str(rng.randint(1, 254)) for _ in range(4))
        port = rng.choice(["", "", ":8080", ":8000", ":4443"])
        return f"{scheme}://{ip}{port}{path}", ip
    if kind == "brand_sub":
        reg = f"{rng.choice(SECURE_WORDS)}-{rng.choice(PHISH_WORDS)}.{tld}"
        return f"{scheme}://{rng.choice(BRANDS)}.{rng.choice(['com', 'net', 'co'])}.{reg}{path}", reg
    if kind == "hyphen":
        parts = [rng.choice(SECURE_WORDS) for _ in range(rng.randint(2, 4))] + [rng.choice(PHISH_WORDS)]
        reg = f"{'-'.join(parts)}.{tld}"
        return f"{scheme}://{reg}{path}", reg
    if kind == "random":
        reg = f"{_rand_id(rng, rng.randint(10, 18))}.{tld}"
        return f"{scheme}://{reg}{path}", reg
    if kind == "at":
        reg = f"{rng.choice(PHISH_WORDS)}{rng.choice(SECURE_WORDS)}.{tld}"
        return f"{scheme}://{rng.choice(BRANDS)}.com@{reg}{path}", reg
    if kind == "puny":
        reg = f"xn--{_rand_id(rng, 6)}-{rng.choice(['43d', '9ra', 'k1a'])}.{tld}"
        return f"{scheme}://{reg}{path}", reg
    if kind == "short_like":
        reg = f"{rng.choice(PHISH_WORDS)}{rng.randint(1, 99)}.{rng.choice(['ly', 'gl', 'co'])}"
        return f"{scheme}://{reg}/{_rand_id(rng, 6)}", reg
    # "compromised": clean-looking domain, phishing-style path (hard cases for a URL-only model)
    reg = f"{rng.choice(PHISH_WORDS)}{rng.choice(BENIGN_SUFFIX)}.{rng.choice(['com', 'net', 'org'])}"
    if kind == "compromised2":
        return f"https://www.{reg}{rng.choice(['/wp-content/plugins/x/login.php', '/images/secure/verify.html'])}", reg
    return f"https://www.{reg}{path}", reg


def generate(n_per_class: int, seed: int) -> list[tuple[str, int]]:
    rng = random.Random(seed)
    rows: dict[str, int] = {}
    owner: dict[str, int] = {}  # registered domain -> label, so no domain appears in both classes

    for label, maker in ((0, benign_url), (1, phishing_url)):
        made = 0
        attempts = 0
        while made < n_per_class and attempts < n_per_class * 40:
            attempts += 1
            url, reg = maker(rng)
            if url in rows or owner.get(reg, label) != label:
                continue
            owner[reg] = label
            rows[url] = label
            made += 1
    items = list(rows.items())
    rng.shuffle(items)
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-class", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    rows = generate(args.per_class, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["url", "label", "source"])
        for url, label in rows:
            writer.writerow([url, label, "synthetic-demo"])
    phishing = sum(label for _u, label in rows)
    print(f"Wrote {len(rows)} rows ({phishing} phishing, {len(rows) - phishing} benign) to {args.output}")
    print("REMINDER: synthetic demo data. Metrics from it are not representative of real-world performance.")


if __name__ == "__main__":
    main()
