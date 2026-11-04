"""Vercel serverless entry point for the PhishGuard AI API.

Vercel routes every /api/* request here (see vercel.json). The function filesystem is
read-only except for /tmp, and each cold start gets a fresh /tmp, so the scan history
database is ephemeral in this deployment. Locally nothing changes: run uvicorn as before.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# /tmp is the only writable location on Vercel; set before the settings cache is built.
os.environ.setdefault("PHISHGUARD_DB_PATH", "/tmp/phishguard.db")
# api/model is trained against the scikit-learn version pinned in requirements.txt;
# backend/ml/artifacts follows the local venv instead, and the loader demands an exact match.
os.environ.setdefault("PHISHGUARD_MODEL_DIR", str(Path(__file__).resolve().parent / "model"))

from app.database.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

# The ASGI lifespan hook does not run under Vercel's Python runtime, so do it here.
init_db()
