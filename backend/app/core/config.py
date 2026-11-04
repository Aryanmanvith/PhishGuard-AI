"""Application settings (standard library only).

Values come from environment variables prefixed with PHISHGUARD_, or from the
.env file in the project root (real environment variables win). Nothing here is
secret: PhishGuard has no API keys by default. See .env.example.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
ENV_PREFIX = "PHISHGUARD_"


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parser (comments and blank lines ignored, no variable expansion)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class Settings:
    app_name: str
    version: str
    cors_origins: str
    db_path: Path
    # Empty means SQLite at db_path; set it to use Postgres instead (see app/database/postgres.py).
    database_url: str
    model_dir: Path
    rate_limit_per_minute: int
    max_body_bytes: int

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def load_settings() -> Settings:
    dotenv = _read_dotenv(PROJECT_DIR / ".env")

    def get(name: str, default: str) -> str:
        key = ENV_PREFIX + name
        return os.environ.get(key) or dotenv.get(key) or default

    return Settings(
        app_name="PhishGuard AI",
        version="1.0.0",
        # Comma-separated browser origins allowed to call the API (CORS).
        cors_origins=get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
        db_path=Path(get("DB_PATH", str(BACKEND_DIR / "data" / "phishguard.db"))),
        # Hosts that provide Postgres set DATABASE_URL / POSTGRES_URL without our prefix.
        database_url=get("DATABASE_URL", "") or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "",
        model_dir=Path(get("MODEL_DIR", str(BACKEND_DIR / "ml" / "artifacts"))),
        # Basic abuse protection per client IP (in-memory, resets on restart).
        rate_limit_per_minute=int(get("RATE_LIMIT_PER_MINUTE", "120")),
        # Reject request bodies larger than this many bytes.
        max_body_bytes=int(get("MAX_BODY_BYTES", "100000")),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
