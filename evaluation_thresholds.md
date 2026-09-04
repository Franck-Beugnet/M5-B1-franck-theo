# Seuils d'évaluation continue — Pyrenex scoring v2

> Doit être lisible par Sophie Léger (Lead Data) et le DPO. **Chaque seuil
> est justifié** par une raison chiffrée.

Jeu de référence : `data/reference_set.csv` (500 lignes, sous-échantillon
stratifié figé du holdout M1, ratio de défauts préservé ~18,4 %).

## Stratégies considérées

| Stratégie | Principe | Avantage | Limite |
|---|---|---|---|
| **Absolu** | Bloquer si métrique < seuil fixe (ex. F1 macro ≥ 0.55) | Simple, lisible pour le DPO ; protège contre un modèle devenu inacceptable en valeur absolue | Ne détecte pas une dérive progressive tant que le seuil fixe n'est pas franchi ; seuil arbitraire s'il n'est adossé à rien |
| **Relatif** | Bloquer si baisse > X vs golden run (ex. -0.05 max) | Détecte toute régression par rapport à l'état de référence connu, même à un niveau encore « correct » en absolu | Ne protège pas si le golden run était déjà médiocre ; inutile (faux rouges) si la tolérance est sous le bruit d'échantillonnage du jeu |
| **Hybride** (retenue) | Les deux combinés | Couvre les deux risques : dérive progressive **et** modèle structurellement mauvais | Deux seuils à maintenir et justifier au lieu d'un |

**Stratégie retenue : hybride.** Un plancher absolu seul ne détecte pas une
dérive progressive silencieuse ; une tolérance relative seule ne protège pas
contre un modèle qui a toujours été médiocre. Les deux ensemble couvrent les
deux risques, au prix d'un seuil de plus à documenter — jugé acceptable vu
l'enjeu (scoring crédit).

## Deux baselines, à ne pas confondre

| | Mesurée sur | Sert à |
|---|---|---|
| **Baseline communiquée** (`metrics_holdout`) | le holdout M1 complet (~6 000 lignes) | ce qu'on a annoncé au client |
| **Golden run** (`data/reference_baseline.json`) | **notre** jeu de référence (500 lignes), au gel | **arbitrer les releases** |

⚠️ Le garde-fou compare au **golden run**, jamais à la baseline communiquée :
les deux jeux n'ont ni la même taille ni la même composition, donc l'écart
entre eux mesurerait une **différence de population**, pas une dégradation
du modèle.

## Seuils

| Métrique | Golden run | Plancher absolu | Baisse max vs golden run | Justification |
|---|---|---|---|---|
| F1 macro | 0.5968 | 0.55 | 0.05 | Plancher fixé ~0.045 sous le golden run : sous 0.55, le modèle échoue à équilibrer les deux classes de façon acceptable pour un usage métier. La baisse max (0.05) est **au-dessus** du 2σ bootstrap mesuré (0.046, cf. table ci-dessous). |
| F1 default | 0.4251 | 0.35 | 0.08 | Le F1 sur la classe défaut est la métrique la plus bruitée (peu de positifs) : plancher large pour éviter les faux rouges, mais qui reste au-dessus du F1 test interne du modèle (0.4287) moins une marge raisonnable. Baisse max = 0.08, > 2σ (0.072). |
| ROC-AUC | 0.7250 | 0.65 | 0.06 | 0.65 correspond à un pouvoir discriminant encore exploitable en scoring crédit (très en dessous, le modèle n'apporte plus rien vs un tri aléatoire pondéré). Baisse max = 0.06, > 2σ (0.053). |
| Recall défaut | 0.6630 | 0.50 | 0.10 | Métrique métier prioritaire (défauts manqués = coût direct) : plancher à 0.50 car en dessous, plus d'un défaut sur deux passerait inaperçu. Tolérance la plus large (0.10) car c'est la métrique la plus bruitée sur 500 lignes (peu de positifs) — reste > 2σ (0.097). |

> **Comment la colonne « baisse max » a été dimensionnée** : bootstrap à 500
> tirages avec remise sur `data/reference_set.csv` (script ci-dessous), on
> retient **au moins 2σ** pour éviter qu'une tolérance ne se déclenche sur du
> hasard d'échantillonnage plutôt que sur une vraie dégradation.

| Métrique | σ bootstrap mesuré | 2 σ | Tolérance retenue |
|---|---|---|---|
| F1 macro | 0.0232 | 0.0464 | 0.05 |
| F1 default | 0.0362 | 0.0724 | 0.08 |
| ROC-AUC | 0.0263 | 0.0526 | 0.06 |
| Recall défaut | 0.0486 | 0.0972 | 0.10 |

Script de mesure du bruit (bootstrap, `random_state`/`rng` fixé pour
reproductibilité) : [`scripts/bootstrap_noise.py`](./scripts/bootstrap_noise.py).

```bash
python scripts/bootstrap_noise.py
```

## Procédure de mise à jour des seuils

- **Qui** : le binôme propriétaire du modèle (revue croisée avant merge).
- **Quand** : à chaque changement du jeu de référence, ou si un golden run
  regelé change sensiblement les métriques de référence.
- **Comment** : garder `THRESHOLDS` dans `scripts/evaluate_model.py` **et** ce
  fichier cohérents (même valeurs). Si `data/reference_set.csv` change,
  regeler le golden run (`--freeze-baseline`) et recalculer le bootstrap
  ci-dessus avant de retoucher les tolérances.
