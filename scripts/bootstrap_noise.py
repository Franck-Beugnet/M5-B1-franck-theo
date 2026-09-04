"""Mesure le bruit d'échantillonnage (bootstrap) des 4 métriques cibles sur
data/reference_set.csv, pour dimensionner les tolérances de
evaluation_thresholds.md (retenir au moins 2 sigma).

Usage::

    python scripts/bootstrap_noise.py
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score, roc_auc_score

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "services" / "model" / "models"
REFERENCE_SET = ROOT / "data" / "reference_set.csv"

N_BOOTSTRAP = 500
RANDOM_STATE = 42


def main() -> None:
    model = joblib.load(MODELS_DIR / "pyrenex_risk_v2.joblib")
    meta = json.loads((MODELS_DIR / "pyrenex_risk_v2.json").read_text(encoding="utf-8"))
    df = pd.read_csv(REFERENCE_SET)

    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    X = df[feature_columns]
    y = df[meta["target_column"]].map(meta["target_mapping"]).to_numpy()
    proba = model.predict_proba(X)[:, 1]
    pred = model.predict(X)

    rng = np.random.default_rng(RANDOM_STATE)
    n = len(y)
    scores: dict[str, list[float]] = {
        "f1_macro": [],
        "f1_default": [],
        "roc_auc": [],
        "recall_default": [],
    }
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, n)
        yb, predb, probab = y[idx], pred[idx], proba[idx]
        if yb.sum() in (0, n):  # les deux classes doivent être présentes
            continue
        scores["f1_macro"].append(f1_score(yb, predb, average="macro"))
        scores["f1_default"].append(f1_score(yb, predb, pos_label=1))
        scores["roc_auc"].append(roc_auc_score(yb, probab))
        scores["recall_default"].append(recall_score(yb, predb, pos_label=1))

    for name, values in scores.items():
        sigma = np.std(values)
        print(f"{name}: sigma={sigma:.4f}  2 sigma={2 * sigma:.4f}")


if __name__ == "__main__":
    main()
