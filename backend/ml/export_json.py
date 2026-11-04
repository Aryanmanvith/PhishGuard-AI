"""Export a trained pipeline to model.json (numpy-only inference).

    python -m ml.export_json --model-dir ml/artifacts --output-dir ../api/model

scikit-learn and scipy together are larger than some serverless bundle budgets, but the
trained model is a standardizer plus a logistic regression: a few hundred floats. This
writes those numbers as JSON, alongside a metrics.json whose model_sha256 matches the
JSON file, so MLService's integrity check works exactly as it does for the pickle.

Run this from the backend folder with scikit-learn installed. The deployment only needs numpy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.json_model import MODEL_JSON_FORMAT  # noqa: E402
from app.services.ml_service import METRICS_FILE, MODEL_FILE, sha256_of  # noqa: E402
from app.services.url_features import FEATURE_NAMES  # noqa: E402


def export(model_dir: Path, out_dir: Path) -> int:
    import joblib

    model_path, meta_path = model_dir / MODEL_FILE, model_dir / METRICS_FILE
    if not model_path.is_file() or not meta_path.is_file():
        print(f"No trained model in {model_dir}. Run `python -m ml.train --demo` first.", file=sys.stderr)
        return 1

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("model_sha256") != sha256_of(model_path):
        print("Model file failed its integrity check (hash mismatch). Re-run the training script.", file=sys.stderr)
        return 1
    if meta.get("feature_names") != list(FEATURE_NAMES):
        print("Model was trained with a different feature set. Re-run the training script.", file=sys.stderr)
        return 1

    pipeline = joblib.load(model_path)
    scaler, clf = pipeline.named_steps["scaler"], pipeline.named_steps["clf"]
    if getattr(clf, "coef_", None) is None or clf.coef_.shape[0] != 1:
        print("Only a binary logistic regression can be exported to JSON.", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    out_model = out_dir / "model.json"
    out_model.write_text(
        json.dumps(
            {
                "format": MODEL_JSON_FORMAT,
                "exported_from": meta.get("model_type", "model"),
                "sklearn_version": meta.get("sklearn_version"),
                "feature_names": list(FEATURE_NAMES),
                "scaler": {"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()},
                "clf": {"coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0])},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # The loader hashes whichever model file it reads, so point metrics.json at this one.
    meta["model_sha256"] = sha256_of(out_model)
    meta["model_format"] = MODEL_JSON_FORMAT
    (out_dir / METRICS_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {out_model} ({out_model.stat().st_size} bytes) and {out_dir / METRICS_FILE}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", type=Path, default=BACKEND_DIR / "ml" / "artifacts")
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    return export(a.model_dir, a.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
