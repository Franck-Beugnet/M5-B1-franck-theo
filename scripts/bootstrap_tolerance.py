from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "services" / "model" / "models"
DEFAULT_REFERENCE_SET = ROOT / "data" / "reference_set.csv"


def compute_bootstrap_stats(
    model,
    X: pd.DataFrame,
    y: np.ndarray,
    n_bootstrap: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    """Estimate metric noise with bootstrap resampling."""
    rng = np.random.default_rng(seed)
    n = len(y)
    values: dict[str, list[float]] = {
        "f1_macro": [],
        "f1_default": [],
        "roc_auc": [],
        "recall_default": [],
    }

    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, n)
        Xb = X.iloc[idx]
        yb = y[idx]
        y_pred = model.predict(Xb)
        y_proba = model.predict_proba(Xb)[:, 1]

        values["f1_macro"].append(float(f1_score(yb, y_pred, average="macro")))
        values["f1_default"].append(float(f1_score(yb, y_pred, pos_label=1)))
        values["roc_auc"].append(float(roc_auc_score(yb, y_proba)))
        values["recall_default"].append(float(recall_score(yb, y_pred, pos_label=1)))

    result: dict[str, dict[str, float]] = {}
    for metric_name, samples in values.items():
        sigma = float(np.std(samples, ddof=1))
        result[metric_name] = {
            "mean": float(np.mean(samples)),
            "sigma": sigma,
            "two_sigma": float(2 * sigma),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate bootstrap noise (sigma, 2*sigma) for reference-set metrics"
    )
    parser.add_argument("--reference-set", type=Path, default=DEFAULT_REFERENCE_SET)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    model_path = MODELS_DIR / "pyrenex_risk_v2.joblib"
    meta_path = MODELS_DIR / "pyrenex_risk_v2.json"

    if not args.reference_set.exists():
        raise SystemExit(f"Reference set not found: {args.reference_set}")
    if not model_path.exists() or not meta_path.exists():
        raise SystemExit(f"Model artifacts missing in {MODELS_DIR}")
    if args.n_bootstrap < 100:
        raise SystemExit("n-bootstrap must be >= 100 for a stable estimate")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    model = joblib.load(model_path)
    df = pd.read_csv(args.reference_set)

    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    target_col = meta["target_column"]
    mapping = meta["target_mapping"]

    missing = [c for c in feature_columns + [target_col] if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns in reference set: {missing}")

    X = df[feature_columns]
    y_series = df[target_col].map(mapping)
    if y_series.isna().any():
        bad_labels = sorted(df.loc[y_series.isna(), target_col].astype(str).unique())
        raise SystemExit(f"Unexpected target labels in reference set: {bad_labels}")
    y = y_series.to_numpy()

    stats = compute_bootstrap_stats(
        model=model,
        X=X,
        y=y,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
    )

    payload = {
        "reference_set": str(args.reference_set.relative_to(ROOT)).replace("\\", "/"),
        "n_reference": int(len(df)),
        "n_bootstrap": int(args.n_bootstrap),
        "seed": int(args.seed),
        "noise": stats,
    }

    text = json.dumps(payload, indent=2)
    print(text)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Saved bootstrap report to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
