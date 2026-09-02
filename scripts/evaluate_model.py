from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import mlflow
import pandas as pd
from sklearn.metrics import f1_score, recall_score, roc_auc_score

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "services" / "model" / "models"
REFERENCE_SET = ROOT / "data" / "reference_set.csv"
REFERENCE_BASELINE = ROOT / "data" / "reference_baseline.json"

# Hybrid strategy: absolute floor + tolerated drop versus golden run.
THRESHOLDS: dict[str, dict[str, float]] = {
    "f1_macro": {"absolute_min": 0.58, "max_drop_vs_baseline": 0.05},
    "f1_default": {"absolute_min": 0.56, "max_drop_vs_baseline": 0.06},
    "roc_auc": {"absolute_min": 0.66, "max_drop_vs_baseline": 0.05},
    "recall_default": {"absolute_min": 0.55, "max_drop_vs_baseline": 0.08},
}


def compute_metrics(model, df: pd.DataFrame, meta: dict) -> dict[str, float]:
    """Calcule les 4 métriques cibles sur le jeu de référence."""
    features = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    target_col = meta["target_column"]
    mapping = meta["target_mapping"]

    missing = [c for c in features + [target_col] if c not in df.columns]
    if missing:
        raise SystemExit(f"Colonnes manquantes dans {REFERENCE_SET}: {missing}")

    X = df[features]
    y = df[target_col].map(mapping)
    if y.isna().any():
        invalid = sorted(df.loc[y.isna(), target_col].astype(str).unique())
        raise SystemExit(f"Valeurs cibles non reconnues dans {REFERENCE_SET}: {invalid}")

    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    return {
        "f1_macro": float(f1_score(y, y_pred, average="macro")),
        "f1_default": float(f1_score(y, y_pred, pos_label=1)),
        "roc_auc": float(roc_auc_score(y, y_proba)),
        "recall_default": float(recall_score(y, y_pred, pos_label=1)),
    }


def check_thresholds(metrics: dict[str, float], baseline: dict[str, float]) -> list[str]:
    """Retourne la liste des violations de seuil (vide = release OK)."""
    violations: list[str] = []
    for metric_name, rules in THRESHOLDS.items():
        value = metrics[metric_name]
        absolute_min = rules["absolute_min"]
        max_drop = rules["max_drop_vs_baseline"]
        baseline_value = baseline[metric_name]
        drop = baseline_value - value

        if value < absolute_min:
            violations.append(
                f"{metric_name}: {value:.6f} < absolute_min {absolute_min:.6f}"
            )
        if drop > max_drop:
            violations.append(
                f"{metric_name}: drop {drop:.6f} > max_drop_vs_baseline {max_drop:.6f} "
                f"(baseline={baseline_value:.6f}, current={value:.6f})"
            )
    return violations


def load_baseline() -> dict[str, float]:
    """Charge les métriques du golden run versionné."""
    if not REFERENCE_BASELINE.exists():
        raise SystemExit(
            f"{REFERENCE_BASELINE} est absent. Lancez d'abord:\n"
            "python scripts/evaluate_model.py --freeze-baseline"
        )

    payload = json.loads(REFERENCE_BASELINE.read_text(encoding="utf-8"))
    if "metrics" not in payload or not isinstance(payload["metrics"], dict):
        raise SystemExit(
            f"Format invalide dans {REFERENCE_BASELINE}: clé 'metrics' manquante"
        )
    return payload["metrics"]


def freeze_baseline(model, df: pd.DataFrame, meta: dict, force: bool = False) -> dict:
    """Mesure et gèle le golden run sur le jeu de référence."""
    if REFERENCE_BASELINE.exists() and not force:
        raise SystemExit(
            f"{REFERENCE_BASELINE} existe déjà. Utilisez --force-freeze pour regeler explicitement."
        )

    metrics = compute_metrics(model, df, meta)
    payload = {
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "reference_set": str(REFERENCE_SET.relative_to(ROOT)).replace("\\", "/"),
        "n_reference": int(len(df)),
        "metrics": {k: round(v, 6) for k, v in metrics.items()},
    }
    REFERENCE_BASELINE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def load_reference_set() -> pd.DataFrame:
    """Charge le jeu de référence, avec un garde-fou sur sa validité."""
    if not REFERENCE_SET.exists():
        raise SystemExit(
            f"{REFERENCE_SET} est absent."
        )
    df = pd.read_csv(REFERENCE_SET)
    if len(df) < 100 or df.iloc[:, -1].nunique() < 2:
        raise SystemExit(
            f"{REFERENCE_SET} contient {len(df)} ligne(s) et "
            f"{df.iloc[:, -1].nunique()} classe(s) de cible.\n"
            "Un instrument de mesure a besoin des DEUX classes et d'assez "
            "d'observations de la classe rare"
        )
    return df


def build_mlflow_params(meta: dict, release_tag: str, n_reference: int) -> dict[str, str | int | float]:
    """Build MLflow params from model metadata without hardcoding hyperparameters."""
    params: dict[str, str | int | float] = {
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "release_tag": release_tag,
        "reference_set": REFERENCE_SET.name,
        "n_reference": int(n_reference),
        "dataset_sha256": meta.get("dataset_sha256", "unknown"),
    }

    for key, value in meta.get("hyperparameters", {}).items():
        if isinstance(value, (str, int, float, bool)):
            params[f"hp_{key}"] = value
        else:
            params[f"hp_{key}"] = json.dumps(value, ensure_ascii=True)
    return params


def maybe_degrade_reference_set(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """Simule un bug de preprocessing en désalignant X et y."""
    degraded = df.copy()
    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    shuffled_features = degraded[feature_columns].sample(frac=1.0, random_state=999).reset_index(
        drop=True
    )
    degraded.loc[:, feature_columns] = shuffled_features
    return degraded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-tag", default="dev")
    parser.add_argument("--degrade", action="store_true")
    parser.add_argument("--freeze-baseline", action="store_true")
    parser.add_argument("--force-freeze", action="store_true")
    args = parser.parse_args()

    model_path = MODELS_DIR / "pyrenex_risk_v2.joblib"
    meta_path = MODELS_DIR / "pyrenex_risk_v2.json"
    if not model_path.exists() or not meta_path.exists():
        raise SystemExit(f"Artifacts modèle manquants dans {MODELS_DIR}")

    model = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    df = load_reference_set()

    if args.freeze_baseline:
        print(json.dumps(freeze_baseline(model, df, meta, force=args.force_freeze), indent=2))
        return 0

    if args.degrade:
        df = maybe_degrade_reference_set(df, meta)

    metrics = compute_metrics(model, df, meta)
    baseline = load_baseline()
    violations = check_thresholds(metrics, baseline)

    mlflow.set_experiment("pyrenex-eval-continue")
    with mlflow.start_run(run_name=args.release_tag):
        mlflow.log_params(build_mlflow_params(meta, args.release_tag, len(df)))
        mlflow.log_metrics(metrics)
        mlflow.set_tag("release_blocked", str(bool(violations)))

    deltas = {k: round(metrics[k] - baseline[k], 6) for k in baseline.keys()}
    output = {
        "release_tag": args.release_tag,
        "reference_set": str(REFERENCE_SET.relative_to(ROOT)).replace("\\", "/"),
        "metrics": {k: round(v, 6) for k, v in metrics.items()},
        "baseline": baseline,
        "deltas_vs_baseline": deltas,
        "violations": violations,
        "release_blocked": bool(violations),
    }
    print(json.dumps(output, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
