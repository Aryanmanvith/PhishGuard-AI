"""Shared test fixtures.

Every test that touches the database or model gets its OWN temporary folder, so
tests never read or write your real data/phishguard.db or trained model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import app...` and `import ml...` work no matter where pytest is started from.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.database.db import init_db  # noqa: E402
from app.services.ml_service import get_ml_service  # noqa: E402


def _reset_caches() -> None:
    get_settings.cache_clear()
    get_ml_service.cache_clear()


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """Temp SQLite file + an EMPTY model folder (so the ML model is 'not trained')."""
    monkeypatch.setenv("PHISHGUARD_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PHISHGUARD_MODEL_DIR", str(tmp_path / "no_model"))
    _reset_caches()
    init_db()
    yield tmp_path
    _reset_caches()


@pytest.fixture()
def client(isolated_env):
    """FastAPI TestClient against a fresh app. Skips cleanly if fastapi/httpx are not installed."""
    testclient = pytest.importorskip("fastapi.testclient")
    from app.main import create_app

    with testclient.TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def trained_model_dir(tmp_path, monkeypatch):
    """Train the demo model (synthetic data) into a temp folder and return the folder."""
    from ml import train

    out = tmp_path / "model"
    monkeypatch.setattr(sys, "argv", ["train", "--demo", "--output-dir", str(out)])
    assert train.main() == 0
    return out
