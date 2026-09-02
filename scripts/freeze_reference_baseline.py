from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import f1_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "services" / "model" / "models"
REFERENCE_SET = ROOT / "data" / "reference_set.csv"
BASELINE_PATH = ROOT / "data" / "reference_baseline.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_metrics(model, df: pd.DataFrame, meta: dict) -> tuple[dict[str, float], dict[str, int]]:
    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    missing_cols = [c for c in feature_columns + [meta["target_column"]] if c not in df.columns]
    if missing_cols:
        raise SystemExit(f"reference_set is missing required columns: {missing_cols}")

    X = df[feature_columns]
    target_col = meta["target_column"]
    mapping = meta["target_mapping"]
    y = df[target_col].map(mapping)

    if y.isna().any():
        bad_values = sorted(df.loc[y.isna(), target_col].astype(str).unique())
        raise SystemExit(f"Unexpected target labels in reference set: {bad_values}")

    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    metrics = {
        "f1_macro": float(f1_score(y, y_pred, average="macro")),
        "f1_default": float(f1_score(y, y_pred, pos_label=1)),
        "roc_auc": float(roc_auc_score(y, y_proba)),
        "recall_default": float(recall_score(y, y_pred, pos_label=1)),
    }

    class_distribution = df[target_col].value_counts().to_dict()
    return metrics, class_distribution


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze golden-run baseline on reference_set.csv")
    parser.add_argument("--reference-set", type=Path, default=REFERENCE_SET)
    parser.add_argument("--output", type=Path, default=BASELINE_PATH)
    parser.add_argument("--force", action="store_true", help="Overwrite baseline file if it already exists")
    args = parser.parse_args()

    model_path = MODELS_DIR / "pyrenex_risk_v2.joblib"
    meta_path = MODELS_DIR / "pyrenex_risk_v2.json"

    if not args.reference_set.exists():
        raise SystemExit(f"Missing reference set: {args.reference_set}")
    if not model_path.exists() or not meta_path.exists():
        raise SystemExit("Missing model artifacts in services/model/models")
    if args.output.exists() and not args.force:
        raise SystemExit(
            f"{args.output} already exists. Use --force only if you intentionally want to re-freeze baseline."
        )

    model = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    reference_df = pd.read_csv(args.reference_set)

    metrics, class_distribution = compute_metrics(model, reference_df, meta)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "reference_set": str(args.reference_set.relative_to(ROOT)).replace("\\", "/"),
        "n_reference": int(len(reference_df)),
        "class_distribution": class_distribution,
        "reference_set_sha256": sha256_file(args.reference_set),
        "model_artifact_sha256": sha256_file(model_path),
        "metrics": {k: round(v, 6) for k, v in metrics.items()},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {args.output}")
    print(json.dumps(payload["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
