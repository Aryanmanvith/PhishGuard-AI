"""Train and evaluate the URL phishing classifier.

Run from the backend folder:
    python -m ml.train --demo                       # offline demo on synthetic sample data
    python -m ml.train --data data/processed/urls_clean.csv \\
        --dataset-name "PhiUSIIL Phishing URL Dataset (UCI)" \\
        --source "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"

Design (explain this in interviews):
  1. Features: 27 numeric features computed from the URL STRING only (same code the API uses).
  2. Leakage prevention: rows are split with GroupShuffleSplit using the registered domain as
     the group, so one domain never appears in both train and test. The scaler lives inside the
     scikit-learn Pipeline, so it is fitted on training data only. Exact duplicate URLs are removed.
  3. Models: Logistic Regression (the deployed, explainable model) and a Random Forest baseline,
     both evaluated on the same held-out test set.
  4. Honest reporting: every number written to metrics.json was computed by this script on the
     held-out test set. Nothing is hard-coded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.ml_service import METRICS_FILE, MODEL_FILE
from app.services.url_features import FEATURE_LABELS, FEATURE_NAMES, InvalidURLError, extract_vector

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEMO_DATA = BACKEND_DIR / "data" / "sample_urls.csv"
DEFAULT_OUT = BACKEND_DIR / "ml" / "artifacts"

MODEL_LIMITATIONS = [
    "Uses only lexical features of the URL string; it never sees page content, domain age or reputation.",
    "Learns the biases of its training set. Public datasets differ from live traffic and age quickly.",
    "Scores are not calibrated probabilities.",
]


def load_urls(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["url", "label"], dtype={"url": str})
    df = df.dropna()
    df["label"] = df["label"].astype(int)
    if not set(df["label"].unique()) <= {0, 1}:
        raise SystemExit("ERROR: label column must contain only 0 (benign) and 1 (phishing).")
    return df.drop_duplicates(subset="url").reset_index(drop=True)


def build_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    rows, labels, groups, skipped = [], [], [], 0
    for url, label in zip(df["url"], df["label"]):
        try:
            _parsed, signals, vector = extract_vector(url)
        except InvalidURLError:
            skipped += 1
            continue
        rows.append([vector[name] for name in FEATURE_NAMES])
        labels.append(label)
        groups.append(signals.registered_domain)
    return np.array(rows, dtype=float), np.array(labels, dtype=int), np.array(groups), skipped


def grouped_split(
    y: np.ndarray, groups: np.ndarray, test_size: float, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Train/test split where every registered domain lives on exactly one side (prevents leakage)."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(np.zeros(len(y)), y, groups))
    overlap = set(groups[train_idx]) & set(groups[test_idx])
    assert not overlap, f"Data leakage: {len(overlap)} domains appear in both train and test"
    return train_idx, test_idx


def evaluate(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    cm = confusion_matrix(y_test, pred, labels=[0, 1])
    return {
        "threshold": 0.5,
        "n_test": int(len(y_test)),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4) if len(set(y_test)) == 2 else None,
        "confusion_matrix": cm.tolist(),  # [[TN, FP], [FN, TP]]
        "confusion_matrix_labels": ["benign", "phishing"],
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="Train on the bundled SYNTHETIC sample (offline demo)")
    src.add_argument("--data", type=Path, help="CSV with columns url,label (label 1 = phishing)")
    ap.add_argument("--dataset-name", default="Custom dataset")
    ap.add_argument("--source", default="(not specified)")
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    data_path = DEMO_DATA if args.demo else args.data
    if not data_path.is_file():
        print(f"ERROR: dataset not found: {data_path}\n"
              "For the demo run `python -m ml.generate_sample_data` first (setup.bat does this).", file=sys.stderr)
        return 1

    df = load_urls(data_path)
    X, y, groups, skipped = build_matrix(df)
    if len(set(y)) < 2:
        print("ERROR: dataset must contain both phishing and benign examples.", file=sys.stderr)
        return 1

    # --- leakage-safe split: all URLs of one registered domain stay on the same side ---
    train_idx, test_idx = grouped_split(y, groups, args.test_size, args.seed)
    X_train, X_test, y_train, y_test = X[train_idx], X[test_idx], y[train_idx], y[test_idx]
    if len(set(y_train)) < 2 or len(set(y_test)) < 2:
        print("ERROR: train or test split is missing a class; use more data.", file=sys.stderr)
        return 1

    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=args.seed)),
    ])
    rf = RandomForestClassifier(
        n_estimators=150, min_samples_leaf=2, class_weight="balanced", random_state=args.seed, n_jobs=-1
    )

    # Cross-validation on the TRAINING portion only (also grouped by domain).
    n_splits = max(2, min(5, len(set(groups[train_idx]))))
    cv_scores = cross_val_score(lr, X_train, y_train, groups=groups[train_idx], cv=GroupKFold(n_splits=n_splits), scoring="f1")

    lr.fit(X_train, y_train)
    rf.fit(X_train, y_train)
    lr_metrics = evaluate(lr, X_test, y_test)
    rf_metrics = evaluate(rf, X_test, y_test)

    coefs = lr.named_steps["clf"].coef_[0]
    importance = sorted(
        ({"feature": n, "label": FEATURE_LABELS[n], "coefficient": round(float(c), 4)} for n, c in zip(FEATURE_NAMES, coefs)),
        key=lambda d: abs(d["coefficient"]),
        reverse=True,
    )

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / MODEL_FILE
    # Write to a temp file in the same folder, then replace (never leaves a half-written model).
    with tempfile.NamedTemporaryFile(dir=out_dir, suffix=".tmp", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    joblib.dump(lr, tmp_path)
    tmp_path.replace(model_path)

    is_demo = bool(args.demo)
    meta = {
        "model_type": "Logistic regression on standardized URL features",
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sklearn_version": sklearn.__version__,
        "random_state": args.seed,
        "feature_names": FEATURE_NAMES,
        "dataset": {
            "name": "Synthetic demo sample (ml/generate_sample_data.py)" if is_demo else args.dataset_name,
            "source": "Generated locally - NOT real phishing data" if is_demo else args.source,
            "is_demo_data": is_demo,
            "rows_used": int(len(y)),
            "phishing_rows": int(y.sum()),
            "benign_rows": int(len(y) - y.sum()),
            "skipped_unparseable": int(skipped),
            "note": (
                "Synthetic data for demonstration. These metrics do NOT describe real-world accuracy."
                if is_demo else "Metrics are computed on a held-out, domain-grouped test split."
            ),
        },
        "split": {
            "method": "GroupShuffleSplit by registered domain (no domain in both sets)",
            "test_size": args.test_size,
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "train_domains": int(len(set(groups[train_idx]))),
            "test_domains": int(len(set(groups[test_idx]))),
        },
        "metrics": {"logistic_regression": lr_metrics, "random_forest_baseline": rf_metrics},
        "cross_validation": {
            "method": f"GroupKFold(n_splits={n_splits}) on the training portion, scoring=f1",
            "f1_mean": round(float(cv_scores.mean()), 4),
            "f1_std": round(float(cv_scores.std()), 4),
        },
        "feature_importance": importance,
        "limitations": MODEL_LIMITATIONS,
        "model_sha256": sha256_file(model_path),
    }
    (out_dir / METRICS_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    m = lr_metrics
    print(f"Trained on {len(train_idx)} rows, tested on {len(test_idx)} rows (domain-grouped split, no overlap).")
    print(f"Logistic regression  precision={m['precision']}  recall={m['recall']}  f1={m['f1']}  roc_auc={m['roc_auc']}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]] = {m['confusion_matrix']}")
    print(f"Random forest baseline f1={rf_metrics['f1']}  roc_auc={rf_metrics['roc_auc']}")
    print(f"Saved model + metrics to {out_dir}")
    if is_demo:
        print("NOTE: demo model trained on SYNTHETIC data. Do not quote these numbers as real performance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
