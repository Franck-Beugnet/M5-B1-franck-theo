"""Construit data/reference_set.csv à partir du holdout M1 (lending_club_holdout.csv).

Composition : échantillonnage stratifié par `loan_status`, ~500 lignes,
ratio de défauts préservé (~18.4%, celui du holdout) pour refléter la
distribution de production plutôt qu'un rééquilibrage artificiel.
`random_state` fixé pour la reproductibilité.

⚠️ Ce script gèle le jeu de référence : ne le relancez pas une fois le
modèle en v2.0 (cf. data/README.md) — un jeu qui change rend les métriques
incomparables d'une release à l'autre.

Usage::

    python scripts/build_reference_set.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
HOLDOUT = ROOT / "data" / "lending_club_holdout.csv"
REFERENCE_SET = ROOT / "data" / "reference_set.csv"

N_SAMPLE = 500
RANDOM_STATE = 42
STRATIFY_COLUMN = "loan_status"


def main() -> None:
    if not HOLDOUT.exists():
        raise SystemExit(
            f"{HOLDOUT} est absent.\n"
            "Récupérez-le depuis votre repo M1-B1 ou Discord fil-M5 "
            "(cf. data/README.md — étape 0)."
        )

    df = pd.read_csv(HOLDOUT)
    frac = N_SAMPLE / len(df)

    sample = (
        df.groupby(STRATIFY_COLUMN, group_keys=False)[df.columns]
        .apply(lambda g: g.sample(frac=frac, random_state=RANDOM_STATE))
        .sample(frac=1, random_state=RANDOM_STATE)
        .reset_index(drop=True)
    )

    sample.to_csv(REFERENCE_SET, index=False)

    print(f"{len(sample)} lignes écrites dans {REFERENCE_SET}")
    print(sample[STRATIFY_COLUMN].value_counts(normalize=True))


if __name__ == "__main__":
    main()
