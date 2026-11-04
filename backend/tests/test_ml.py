"""Machine-learning pipeline: training, safe loading, graceful degradation and inference."""
import json

import numpy as np
import pandas as pd

from app.services.ml_service import METRICS_FILE, MODEL_FILE, MLService
from app.services.url_analyzer import analyze_url
from app.services.url_features import FEATURE_NAMES, extract_vector
from ml.train import BACKEND_DIR, build_matrix, grouped_split, sha256_file


def vector_for(url: str) -> dict:
    return extract_vector(url)[2]


def test_missing_model_is_reported_not_raised(tmp_path):
    svc = MLService(tmp_path / "empty")
    assert svc.available is False and "No trained model" in svc.error
    result = svc.predict(vector_for("https://example.com/"))
    assert result.available is False and result.score is None
    assert svc.describe()["available"] is False


def test_trained_model_loads_and_scores(trained_model_dir):
    svc = MLService(trained_model_dir)
    assert svc.available, svc.error
    bad = svc.predict(vector_for("http://paypal.com.secure-login-verify.example.xyz/verify/account"))
    good = svc.predict(vector_for("https://www.example.com/about"))
    assert 0 <= good.score <= 100 and 0 <= bad.score <= 100
    assert bad.score > good.score
    assert bad.label == "phishing-like" and good.label == "benign-like"
    assert bad.trained_on_demo_data is True and "NOT a calibrated probability" in bad.note
    assert bad.top_features and all(f.direction in ("raises", "lowers") for f in bad.top_features)


def test_metrics_file_is_complete_and_consistent(trained_model_dir):
    meta = json.loads((trained_model_dir / METRICS_FILE).read_text(encoding="utf-8"))
    lr = meta["metrics"]["logistic_regression"]
    for key in ("precision", "recall", "f1", "roc_auc", "confusion_matrix"):
        assert key in lr
    cm = np.array(lr["confusion_matrix"])
    assert cm.shape == (2, 2) and cm.sum() == lr["n_test"] == meta["split"]["test_rows"]
    assert meta["dataset"]["is_demo_data"] is True
    assert meta["model_sha256"] == sha256_file(trained_model_dir / MODEL_FILE)
    assert meta["feature_names"] == FEATURE_NAMES


def test_split_has_no_domain_leakage():
    df = pd.read_csv(BACKEND_DIR / "data" / "sample_urls.csv").drop_duplicates(subset="url")
    assert df["url"].is_unique
    _X, y, groups, _skipped = build_matrix(df)
    train_idx, test_idx = grouped_split(y, groups, test_size=0.2, seed=42)
    assert set(groups[train_idx]).isdisjoint(set(groups[test_idx]))
    assert len(train_idx) + len(test_idx) == len(y)


def test_tampered_model_file_is_refused(trained_model_dir):
    with (trained_model_dir / MODEL_FILE).open("ab") as fh:
        fh.write(b"tamper")
    svc = MLService(trained_model_dir)
    assert svc.available is False and "integrity" in svc.error


def test_feature_mismatch_is_refused(trained_model_dir):
    path = trained_model_dir / METRICS_FILE
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["feature_names"] = meta["feature_names"][:-1]
    path.write_text(json.dumps(meta), encoding="utf-8")
    svc = MLService(trained_model_dir)
    assert svc.available is False and "feature set" in svc.error


def test_analyze_url_with_model_compares_results(trained_model_dir):
    r = analyze_url("http://paypal.com.secure-login.example.xyz/verify", MLService(trained_model_dir))
    assert r.ml.available and r.comparison.status in ("agree", "disagree")
    assert "never opened" in " ".join(r.limitations)
