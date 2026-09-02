# Seuils d evaluation continue - Pyrenex scoring v2

Date: 2026-09-02

Jeu de reference: data/reference_set.csv (500 lignes, 250 Charged Off / 250 Fully Paid)
Golden run: data/reference_baseline.json

## Rappel: baseline de comparaison

Deux references existent et ne servent pas au meme usage:

- Baseline communiquee (M1 holdout complet): pour la communication historique.
- Golden run (ce projet): pour arbitrer les releases CI/CD.

Le garde-fou compare uniquement au golden run, jamais au holdout M1.

## Strategies considerees

| Strategie | Regle | Avantages | Limites |
|---|---|---|---|
| Absolue | metric >= plancher fixe | Simple a lire et a auditer | Ignore le niveau reel du modele courant |
| Relative | drop <= tolerance vs golden run | Detecte bien les regressions par rapport au modele de reference | Si tolerance trop faible, alerte sur le bruit de mesure |
| Hybride (retenue) | plancher absolu + drop max | Evite les faux positifs ET evite de valider un modele trop faible en absolu | Demande une calibration initiale plus soignee |

Decision retenue: strategie hybride.

Raison:

- La composante relative detecte une degradation de release vs modele de reference.
- La composante absolue evite de laisser passer une release avec des perfs globalement faibles, meme si la baisse relative est faible.

## Golden run et seuils retenus (4 metriques)

| Metrique | Golden run | Plancher absolu | Baisse max toleree vs golden run | Justification |
|---|---:|---:|---:|---|
| F1 macro | 0.641884 | 0.58 | 0.05 | La tolerance relative depasse 2 sigma bootstrap (0.0434). Le plancher garde une marge raisonnable tout en restant exigeant. |
| F1 defaut | 0.635438 | 0.56 | 0.06 | Tolerance > 2 sigma (0.0506) pour eviter le bruit; plancher fixe un minimum de qualite sur la classe couteuse. |
| ROC-AUC | 0.712016 | 0.66 | 0.05 | Tolerance > 2 sigma (0.0451), donc regression significative seulement. |
| Recall defaut | 0.624000 | 0.55 | 0.08 | Metrique la plus sensible au bruit; tolerance dimensionnee au-dessus de 2 sigma (0.0599) avec marge de securite. |

## Mesure du bruit par bootstrap

Protocole:

- 1000 reechantillonnages bootstrap (avec remise) sur les 500 lignes de data/reference_set.csv.
- Modele et preprocessing inchanges.
- Graine RNG fixe: 42.
- Script versionne utilise: scripts/bootstrap_tolerance.py
- Commande de reproduction:
  py -3.12 scripts/bootstrap_tolerance.py --n-bootstrap 1000 --seed 42

| Metrique | sigma bootstrap | 2 sigma | Tolerance retenue |
|---|---:|---:|---:|
| F1 macro | 0.0217 | 0.0434 | 0.05 |
| F1 defaut | 0.0253 | 0.0506 | 0.06 |
| ROC-AUC | 0.0226 | 0.0451 | 0.05 |
| Recall defaut | 0.0300 | 0.0599 | 0.08 |

Contrainte verifiee: toutes les tolerances relatives retenues sont >= 2 sigma.

## Coherence avec le script

Les seuils ci-dessus sont implementes dans scripts/evaluate_model.py, dictionnaire THRESHOLDS.

- f1_macro: absolute_min=0.58, max_drop_vs_baseline=0.05
- f1_default: absolute_min=0.56, max_drop_vs_baseline=0.06
- roc_auc: absolute_min=0.66, max_drop_vs_baseline=0.05
- recall_default: absolute_min=0.55, max_drop_vs_baseline=0.08

## Procedure de mise a jour

- Qui: owner du modele + reviewer Data (double validation).
- Quand: changement de modele de reference, changement de reference_set, ou evolution majeure metier.
- Comment:
  1. Regenerer/valider le jeu de reference si necessaire.
  2. Regeler le golden run.
  3. Recalculer le bruit bootstrap.
  4. Mettre a jour ce fichier ET THRESHOLDS dans le script dans le meme commit.
  5. Verifier qu un run normal passe (exit 0) et qu un run degrade bloque (exit 1).
