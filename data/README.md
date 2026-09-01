# `data/` — le jeu de référence de M5-B2

> ⚠️ **Le jeu de référence n'est pas fourni. C'est vous qui le construisez.**
> C'est la première tâche de M5-B2, et c'est une **décision de conception**,
> pas une formalité de tirage.

## Ce qu'il y a dans ce dossier

| Fichier | Statut |
|---|---|
| `reference_set_TEMPLATE.csv` | **Exemple de format uniquement** — 20 lignes. Montre les colonnes attendues et leur ordre. Ce n'est **pas** un jeu de référence : 20 lignes ne mesurent rien. Ne le copiez pas en `reference_set.csv`. |
| `reference_set.csv` | **À produire par vous** (~500 lignes), à partir du holdout M1. Versionné avec un commit dédié. |
| `reference_baseline.json` | **À produire par vous**, une seule fois, via `evaluate_model.py --freeze-baseline`. C'est le *golden run*. |

## Étape 0 — récupérer le holdout M1

Le jeu de référence est un **sous-échantillon stable du holdout de M1-B1** :
`lending_club_holdout.csv` (~6 000 lignes, ~18 % de défauts).

Trois façons de le retrouver, dans l'ordre :

1. **Votre repo M1-B1**, dans `data/` — attention, `data/` est gitignoré :
   le fichier est peut-être resté sur votre machine sans avoir été poussé.
2. **Discord `fil-M5`** : le fichier est re-diffusé au lancement de M5-B2.
3. À défaut, demandez-le sur `fil-M5` — ne partez pas sur un autre jeu de
   données, les métriques ne seraient comparables à rien.

Placez-le dans `data/lending_club_holdout.csv` (il est gitignoré, c'est
volontaire : on ne versionne pas le holdout complet, seulement le
sous-échantillon que vous en tirez).

## Étape 1 — en tirer VOTRE jeu de référence

Deux compositions sont défendables, et le choix change vos seuils :

- **refléter la production** (~18 % de défauts, comme le holdout) ;
- **sur-représenter la classe rare** (par exemple 250 / 250).

Ce jeu n'est pas une photo de la production : c'est l'**instrument de mesure**
de votre garde-fou. Un instrument se juge à sa **précision**, et la précision
d'une métrique dépend du nombre d'observations de la classe qu'elle mesure.
Un jeu de 500 lignes à 18 % ne contient que ~90 défauts — demandez-vous ce que
ça fait au bruit de votre `recall_defaut`, donc à la tolérance que vous serez
obligé·e de retenir.

**Tranchez, et écrivez votre raison** dans `evaluation_thresholds.md`
(2-3 lignes). Les deux réponses passent si elles sont argumentées ;
« j'ai fait un `sample(500)` » n'en est pas une.

Puis : `random_state` fixé, commit dédié (*« add reference evaluation set,
v1 »*), et **on n'y touche plus** tant que le modèle est en v2.0 — un jeu de
référence qui bouge rend les métriques incomparables d'une release à l'autre.

📚 Mini-cours : [`../ressources/08_Evaluation_continue_seuils_essentiel.md`](../ressources/08_Evaluation_continue_seuils_essentiel.md)