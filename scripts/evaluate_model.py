"""Évaluation continue + tracking MLflow (M5-B2).

À chaque release : recalcule les métriques cibles sur un jeu de référence
figé, **trace le run dans MLflow**, compare aux seuils, et **sort un code
retour non-zéro** si dégradation (→ bloque la release en CI).

Mini-cours : `07_MLflow_tracking_essentiel.md` + `08_Evaluation_continue_seuils`.

Usage cible::

    python scripts/evaluate_model.py --freeze-baseline             # une fois, au gel du jeu
    python scripts/evaluate_model.py --release-tag v2.0.0
    python scripts/evaluate_model.py --release-tag bad --degrade   # test du rouge
    mlflow ui    # comparer les runs

⚠️ **Le piège central du brief.** La tentation est de comparer vos métriques à
la baseline holdout annoncée en M1 (`metrics_holdout` dans le `.json`). Ne le
faites pas : le holdout et votre jeu de référence n'ont ni la même taille ni la
même composition. Vous mesureriez l'écart entre **deux populations**, pas la
dégradation du **modèle** — et votre garde-fou se déclencherait tout seul.
La baseline du garde-fou, c'est le **golden run** : les métriques mesurées sur
**votre** jeu de référence, au moment où vous le gelez.
"""

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

# Stratégie hybride (plancher absolu + baisse max vs golden run).
# Tolérances relatives dimensionnées par bootstrap (500 tirages, cf.
# evaluation_thresholds.md) : toutes ≥ 2 σ mesuré sur data/reference_set.csv.
THRESHOLDS: dict[str, dict[str, float]] = {
    "f1_macro": {"absolute_min": 0.55, "max_drop_vs_baseline": 0.05},
    "f1_default": {"absolute_min": 0.35, "max_drop_vs_baseline": 0.08},
    "roc_auc": {"absolute_min": 0.65, "max_drop_vs_baseline": 0.06},
    "recall_default": {"absolute_min": 0.50, "max_drop_vs_baseline": 0.10},
}


def compute_metrics(model, df: pd.DataFrame, meta: dict) -> dict[str, float]:
    """Calcule les métriques cibles sur le jeu de référence."""
    feature_columns = meta["feature_columns_numeric"] + meta["feature_columns_categorical"]
    X = df[feature_columns]
    y = df[meta["target_column"]].map(meta["target_mapping"])

    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    return {
        "f1_macro": f1_score(y, y_pred, average="macro"),
        "f1_default": f1_score(y, y_pred, pos_label=1),
        "roc_auc": roc_auc_score(y, y_proba),
        "recall_default": recall_score(y, y_pred, pos_label=1),
    }


def check_thresholds(metrics: dict[str, float], baseline: dict) -> list[str]:
    """Retourne la liste des violations de seuil (vide = release OK)."""
    violations: list[str] = []
    for name, rule in THRESHOLDS.items():
        value = metrics[name]

        absolute_min = rule.get("absolute_min")
        if absolute_min is not None and value < absolute_min:
            violations.append(
                f"{name}={value:.4f} sous le plancher absolu {absolute_min}"
            )

        max_drop = rule.get("max_drop_vs_baseline")
        if max_drop is not None:
            drop = baseline[name] - value
            if drop > max_drop:
                violations.append(
                    f"{name} a baissé de {drop:.4f} vs baseline "
                    f"({baseline[name]:.4f} -> {value:.4f}), tolérance {max_drop}"
                )
    return violations


def load_baseline() -> dict:
    """Charge le golden run (baseline mesurée sur le jeu de référence)."""
    if not REFERENCE_BASELINE.exists():
        raise SystemExit(
            f"{REFERENCE_BASELINE} est absent.\n"
            "Lancez d'abord `python scripts/evaluate_model.py --freeze-baseline`."
        )
    baseline = json.loads(REFERENCE_BASELINE.read_text(encoding="utf-8"))
    return baseline["metrics"]


def freeze_baseline(model, df: pd.DataFrame, meta: dict) -> dict:
    """Mesure et gèle le golden run sur le jeu de référence."""
    metrics = compute_metrics(model, df, meta)
    baseline = {
        "model_version": meta["model_version"],
        "reference_set": REFERENCE_SET.relative_to(ROOT).as_posix(),
        "n_reference": len(df),
        "metrics": metrics,
    }
    REFERENCE_BASELINE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


def load_reference_set() -> pd.DataFrame:
    """Charge le jeu de référence, avec un garde-fou sur sa validité.

    Le jeu de référence est VOTRE instrument de mesure : vous le construisez
    à partir du holdout M1 (cf. `data/README.md`). Le fichier
    `reference_set_TEMPLATE.csv` livré dans le repo est un **exemple de
    format** de 20 lignes, pas un jeu de référence utilisable.
    """
    if not REFERENCE_SET.exists():
        raise SystemExit(
            f"{REFERENCE_SET} est absent.\n"
            "Ce fichier n'est pas fourni : c'est à vous de le construire à "
            "partir du holdout M1 (`data/lending_club_holdout.csv`).\n"
            "Mode d'emploi : data/README.md — étape 0."
        )
    df = pd.read_csv(REFERENCE_SET)
    if len(df) < 100 or df.iloc[:, -1].nunique() < 2:
        raise SystemExit(
            f"{REFERENCE_SET} contient {len(df)} ligne(s) et "
            f"{df.iloc[:, -1].nunique()} classe(s) de cible.\n"
            "Un instrument de mesure a besoin des DEUX classes et d'assez "
            "d'observations de la classe rare (~500 lignes attendues).\n"
            "Avez-vous copié reference_set_TEMPLATE.csv ? C'est un exemple de "
            "format, pas un jeu de référence — cf. data/README.md."
        )
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-tag", default="dev")
    parser.add_argument("--degrade", action="store_true")
    parser.add_argument("--freeze-baseline", action="store_true")
    args = parser.parse_args()

    model = joblib.load(MODELS_DIR / "pyrenex_risk_v2.joblib")
    meta = json.loads((MODELS_DIR / "pyrenex_risk_v2.json").read_text(encoding="utf-8"))
    df = load_reference_set()

    if args.freeze_baseline:
        print(json.dumps(freeze_baseline(model, df, meta), indent=2))
        return 0

    if args.degrade:
        # TODO 4 — simuler un bug de preprocessing réaliste (ex. désaligner
        #   X et y) pour PROUVER que le rouge bloque bien la release.
        pass

    metrics = compute_metrics(model, df, meta)
    baseline = load_baseline()  # ← le golden run, PAS metrics_holdout
    violations = check_thresholds(metrics, baseline)

    # --- Bloc MLflow ---------------------------------------------------------
    mlflow.set_experiment("pyrenex-eval-continue")
    with mlflow.start_run(run_name=args.release_tag):
        params = {
            "model_version": meta["model_version"],
            "release_tag": args.release_tag,
            "reference_set": REFERENCE_SET.relative_to(ROOT).as_posix(),
            "n_reference": len(df),
            "dataset_sha256": meta["dataset_sha256"],
        }
        # Hyperparamètres du modèle lus depuis pyrenex_risk_v2.json — pas recopiés ici.
        params.update({f"hp_{k}": v for k, v in meta["hyperparameters"].items()})
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)  # ← les 4 métriques tracées
        mlflow.set_tag("release_blocked", str(bool(violations)))
    # ------------------------------------------------------------------------

    print(json.dumps({"metrics": metrics, "violations": violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
