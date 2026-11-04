"""A numpy-only stand-in for the trained scikit-learn pipeline.

Why this exists: scikit-learn pulls in scipy, and the two together are far larger than
the serverless bundle budget of some hosts. The trained model is a standardizer followed
by a logistic regression, which is a handful of numbers, so deployments can carry
`model.json` (written by `python -m ml.export_json`) instead of `model.joblib`.

The object returned here exposes only what MLService uses: `predict_proba` and the
`named_steps` pair the per-feature explanation reads. Loading plain JSON also sidesteps
the pickle-execution risk described in ml_service, so no scikit-learn version has to match.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODEL_JSON_FORMAT = "phishguard-logreg-1"


class _Scaler:
    """Mirrors sklearn StandardScaler.transform for a 2-D row array."""

    def __init__(self, mean: Any, scale: Any) -> None:
        self.mean_, self.scale_ = mean, scale

    def transform(self, rows: Any) -> Any:
        return (rows - self.mean_) / self.scale_


class _LogisticRegression:
    """Mirrors sklearn LogisticRegression for the binary case."""

    def __init__(self, coef: Any, intercept: float) -> None:
        self.coef_, self.intercept_ = coef, intercept

    def decision_function(self, scaled: Any) -> Any:
        return scaled @ self.coef_[0] + self.intercept_


class JsonPipeline:
    """Duck-types the parts of sklearn's Pipeline that MLService touches."""

    def __init__(self, scaler: _Scaler, clf: _LogisticRegression) -> None:
        self.named_steps = {"scaler": scaler, "clf": clf}

    def predict_proba(self, rows: Any) -> Any:
        import numpy as np

        scaled = self.named_steps["scaler"].transform(rows)
        z = self.named_steps["clf"].decision_function(scaled)
        p1 = 1.0 / (1.0 + np.exp(-z))          # class 1 = phishing
        return np.column_stack([1.0 - p1, p1])


def load_json_model(path: Path, feature_names: list[str]) -> JsonPipeline:
    """Build a pipeline from `model.json`. Raises ValueError if it does not fit this app."""
    import numpy as np

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != MODEL_JSON_FORMAT:
        raise ValueError(f"Unsupported model.json format: {data.get('format')!r}")
    if data.get("feature_names") != feature_names:
        raise ValueError("model.json was exported for a different feature set")

    n = len(feature_names)
    mean = np.asarray(data["scaler"]["mean"], dtype=float)
    scale = np.asarray(data["scaler"]["scale"], dtype=float)
    coef = np.asarray([data["clf"]["coef"]], dtype=float)
    if mean.shape != (n,) or scale.shape != (n,) or coef.shape != (1, n):
        raise ValueError("model.json has the wrong number of coefficients")
    if not np.all(scale > 0):
        raise ValueError("model.json has a non-positive scale value")

    return JsonPipeline(_Scaler(mean, scale), _LogisticRegression(coef, float(data["clf"]["intercept"])))
