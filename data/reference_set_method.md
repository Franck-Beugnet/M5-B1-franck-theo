# Construction du jeu de reference M5-B2

Date: 2026-09-02

## Objectif

Construire un jeu de reference stable d environ 500 lignes pour l evaluation continue du modele, puis geler un golden run qui servira de point d arbitrage pour les releases suivantes.

Ce jeu sert d instrument de mesure du garde-fou CI/CD. Il ne cherche pas a reproduire exactement la distribution production.

## Source de donnees

- Source: data/lending_club_holdout.csv
- Cible: loan_status
- Mapping du modele:
  - Fully Paid -> 0
  - Charged Off -> 1

## Methode appliquee

### 1. Sous-echantillonnage stable du holdout

Le jeu de reference a ete genere avec un script dedie:

- scripts/build_reference_set.py

Strategie utilisee:

- Taille totale: 500 lignes
- Composition: 250 Charged Off, 250 Fully Paid
- Tirages deterministes avec graines fixes:
  - Charged Off: random_state = 42
  - Fully Paid: random_state = 43
  - Melange final: random_state = 44

Cette methode garantit la reproductibilite: une rerun produit le meme fichier de reference.

### 2. Gel du golden run

Le baseline a ete gele via un second script:

- scripts/freeze_reference_baseline.py

Ce script:

- charge le modele versionne services/model/models/pyrenex_risk_v2.joblib
- charge les metadonnees services/model/models/pyrenex_risk_v2.json
- verifie les colonnes attendues
- calcule 4 metriques sur data/reference_set.csv
- ecrit data/reference_baseline.json avec:
  - metriques
  - version modele
  - taille et composition du jeu
  - empreinte SHA256 du jeu de reference
  - empreinte SHA256 de l artefact modele

## Pourquoi ce choix de composition

Choix retenu: 250/250 (classe equilibree) plutot qu un simple echantillon aleatoire refletant 18 % de defauts.

Raison principale:

- Le garde-fou doit detecter une vraie degradation sur la classe rare.
- Avec environ 18 % de defauts sur 500 lignes, on aurait autour de 90 defauts seulement, ce qui augmente fortement l incertitude sur recall_default et f1_default.
- En passant a 250 defauts, la mesure sur la classe critique est plus stable, donc plus utile pour fixer des seuils defensibles.

En resume:

- Jeu production-like: plus representatif, mais plus bruite pour les metriques de defaut.
- Jeu equilibre: moins representatif de la prod, mais meilleur instrument de surveillance de degradation.

Ici, l objectif prioritaire etait la precision de mesure du garde-fou, donc le choix equilibre.

## Resultats du golden run gele

Fichier: data/reference_baseline.json

Metriques mesurees:

- f1_macro: 0.641884
- f1_default: 0.635438
- roc_auc: 0.712016
- recall_default: 0.624

Composition verifiee:

- n_reference: 500
- Charged Off: 250
- Fully Paid: 250

## Reproductibilite

Commandes utilisees:

    py -3.12 scripts/build_reference_set.py
    py -3.12 scripts/freeze_reference_baseline.py

Note environnement:

- Le venv local etait en Python 3.14.
- Les versions verrouillees de la stack modele sont compatibles avec Python 3.12 pour cette generation.

## Regles de gouvernance

- data/reference_set.csv est versionne et fige tant que le modele de reference ne change pas.
- data/reference_baseline.json est l unique baseline de comparaison en CI/CD.
- Ne pas comparer les releases au score historique holdout M1 (population differente).
- Si le jeu de reference change, il faut regeler explicitement la baseline avec le script dedie.
