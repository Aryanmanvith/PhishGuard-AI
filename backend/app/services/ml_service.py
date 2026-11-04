"""Loads the trained scikit-learn model and scores URL feature vectors.

Safety notes (good interview material):
  * The model is only ever loaded from ONE fixed directory (settings.model_dir).
    No user input ever chooses a file path.
  * joblib files are pickles, and unpickling untrusted data can run code. So we
    only load a file whose SHA-256 matches the hash recorded in metrics.json at
    training time, and we tell users to train their own model locally.
  * If anything is missing or inconsistent, the service reports
    "unavailable" with a reason instead of crashing the API.
"""
from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.risk import ML_FLAG_THRESHOLD
from app.schemas.scan import FeatureContribution, MLResult
from app.services.url_features import FEATURE_LABELS, FEATURE_NAMES

log = logging.getLogger("phishguard.ml")

MODEL_FILE = "model.joblib"
MODEL_JSON_FILE = "model.json"  # numpy-only export, used where scikit-learn is too large to ship
METRICS_FILE = "metrics.json"
NO_MODEL_HINT = "No trained model found. Run `python -m ml.train --demo` from the backend folder (see README)."


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class MLService:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self._pipeline: Any = None
        self._meta: dict[str, Any] | None = None
        self.error: str | None = None
        self.load()

    # ------------------------------------------------------------- loading
    def load(self) -> None:
        self._pipeline, self._meta, self.error = None, None, None
        meta_path = self.model_dir / METRICS_FILE
        # Prefer the pickled pipeline; fall back to the numpy-only JSON export.
        model_path = self.model_dir / MODEL_FILE
        if not model_path.is_file():
            model_path = self.model_dir / MODEL_JSON_FILE
        if not model_path.is_file() or not meta_path.is_file():
            self.error = NO_MODEL_HINT
            return
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.error = "metrics.json could not be read. Re-run the training script."
            return

        if meta.get("model_sha256") != sha256_of(model_path):
            self.error = "Model file failed its integrity check (hash mismatch). Re-run the training script."
            return
        if meta.get("feature_names") != FEATURE_NAMES:
            self.error = "Model was trained with a different feature set. Re-run the training script."
            return

        try:
            if model_path.name == MODEL_JSON_FILE:
                # Plain JSON: no pickle and no scikit-learn, so no version has to match.
                from app.services.json_model import load_json_model
                self._pipeline = load_json_model(model_path, list(FEATURE_NAMES))
            else:
                import sklearn
                if meta.get("sklearn_version") != sklearn.__version__:
                    self.error = (
                        f"Model was trained with scikit-learn {meta.get('sklearn_version')} but "
                        f"{sklearn.__version__} is installed. Re-run the training script."
                    )
                    return
                import joblib
                self._pipeline = joblib.load(model_path)
        except Exception:  # noqa: BLE001 - any load failure must degrade gracefully
            log.exception("Failed to load model")
            self._pipeline = None
            self.error = "Model file could not be loaded. Re-run the training script."
            return
        self._meta = meta

    # ------------------------------------------------------------ properties
    @property
    def available(self) -> bool:
        return self._pipeline is not None

    def describe(self) -> dict[str, Any]:
        """What the dashboard's Model page shows."""
        if not self.available or self._meta is None:
            return {"available": False, "reason": self.error or NO_MODEL_HINT}
        return {"available": True, **self._meta}

    # ------------------------------------------------------------ inference
    def predict(self, features: dict[str, float]) -> MLResult:
        if not self.available or self._meta is None:
            return MLResult(available=False, note=self.error or NO_MODEL_HINT)

        import numpy as np

        row = np.array([[features[name] for name in FEATURE_NAMES]], dtype=float)
        proba = float(self._pipeline.predict_proba(row)[0][1])  # class 1 = phishing
        score = round(proba * 100, 1)
        demo = bool(self._meta.get("dataset", {}).get("is_demo_data", False))

        note = (
            "Model output scaled to 0-100. It is NOT a calibrated probability. "
            "The model only sees lexical features of the URL string."
        )
        if demo:
            note += " This model was trained on small synthetic DEMO data, so treat it as a demonstration only."

        return MLResult(
            available=True,
            score=score,
            label="phishing-like" if score >= ML_FLAG_THRESHOLD else "benign-like",
            model_name=self._meta.get("model_type", "model"),
            trained_on_demo_data=demo,
            top_features=self._explain(row),
            note=note,
        )

    def _explain(self, row: Any, top_n: int = 5) -> list[FeatureContribution]:
        """Per-feature contribution = coefficient x standardized value (logistic regression only)."""
        try:
            scaler = self._pipeline.named_steps["scaler"]
            clf = self._pipeline.named_steps["clf"]
            scaled = scaler.transform(row)[0]
            contributions = clf.coef_[0] * scaled
        except Exception:  # noqa: BLE001 - explanations are best-effort
            return []
        order = sorted(range(len(FEATURE_NAMES)), key=lambda i: abs(contributions[i]), reverse=True)[:top_n]
        out: list[FeatureContribution] = []
        for i in order:
            c = float(contributions[i])
            if abs(c) < 0.05:
                continue
            name = FEATURE_NAMES[i]
            out.append(
                FeatureContribution(
                    feature=name,
                    label=FEATURE_LABELS[name],
                    value=float(row[0][i]),
                    contribution=round(c, 3),
                    direction="raises" if c > 0 else "lowers",
                )
            )
        return out


@lru_cache
def get_ml_service() -> MLService:
    return MLService(get_settings().model_dir)
