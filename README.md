# M5-B1 + M5-B2 — Pyrenex Prod (architecture, CI/CD, monitoring, éval continue)

> **Repo template GitHub.** Un·e des 2 du binôme clique **« Use this
> template »** → `M5-B1-pyrenex-prod-<binome>`, puis ajoute l'autre comme
> collaborateur. Vous partez du **scoring v2** (modèle M1 fourni) et vous le
> mettez en **production complète** : 3 services orchestrés, CI/CD, monitoring
> Grafana, runbook, puis (B2) évaluation continue + tracking MLflow.

---

## 🧭 Votre brief en un coup d'œil

**Ce README est votre document de pilotage unique** — tout ce qu'il faut faire,
dans l'ordre, avec le bon appui. Les autres supports ont chacun un rôle précis :

| Support | Rôle |
|---|---|
| **Simplonline** | Le contrat : contexte client, livrables, critères de performance |
| **Ce README** | Le pilotage : quoi faire, quand, avec quel mini-cours |
| [`ressources/`](./ressources/) | Les 8 mini-cours d'appui (index dans [`ressources/README.md`](./ressources/README.md)) |
| **Discord `fil-M5`** | Annonces + questions |

### M5-B1 — les 2 jours sync (binôme)

> La numérotation des tâches est celle de l'énoncé Simplonline (1 → 12).
> La tâche 4, c'est le déjeuner : elle compte aussi.

| Quand | Tâche | Durée | Appui |
|---|---|---|---|
| Mardi 10h35 | 1. Tirage binôme + appropriation de la reprise M1 (modèle + API fournis) | 45 min | — |
| Mardi 11h20 | 2. Architecture 3 services (`model` / `backend` / `frontend`) — 1ʳᵉ partie | 1h10 | [`01_Docker_compose`](./ressources/01_Docker_compose_multiservices_essentiel.md) |
| Mardi 12h30 | 4. 🍽️ Déjeuner | 1h | — |
| Mardi 13h30 | 2. Architecture 3 services — fin | 20 min | [`01_Docker_compose`](./ressources/01_Docker_compose_multiservices_essentiel.md) |
| Mardi 13h50 | 3. Vérification `docker compose up` | 15 min | [`01_Docker_compose`](./ressources/01_Docker_compose_multiservices_essentiel.md) |
| Mardi 14h05 | 5. Pipeline CI/CD GitHub Actions + *quality gate* (pause 15 min incluse) | 2h30 | [`03_GitHub_Actions`](./ressources/03_GitHub_Actions_CI_CD_essentiel.md) — appui [`06_Pair_coding`](./ressources/06_Pair_coding_sync_long_essentiel.md) |
| Mardi 16h45 | 6. Mur réflexif intermédiaire | 15 min | — |
| Mercredi 9h15 | 7. Endpoint `/metrics` + métriques métier | 30 min | [`02_FastAPI_metrics_Prometheus`](./ressources/02_FastAPI_metrics_Prometheus_essentiel.md) |
| Mercredi 9h45 | 8. Prometheus + Grafana dans le compose | 30 min | [`02_FastAPI_metrics_Prometheus`](./ressources/02_FastAPI_metrics_Prometheus_essentiel.md) |
| Mercredi 10h15 | 9. Dashboard Grafana custom (vie / vitesse / comportement) | 45 min | [`04_Grafana_dashboard`](./ressources/04_Grafana_dashboard_custom_essentiel.md) |
| Mercredi 11h00 | 10. Runbook d'astreinte (4 procédures) | 30 min | [`05_Runbook_astreinte`](./ressources/05_Runbook_astreinte_essentiel.md) |
| Mercredi 11h30 | 11. **Tour de table binômes** (démo compose + dashboard) | 1h | — |
| Mercredi 12h30 | 12. Mur réflexif final M5-B1 + lancement M5-B2 | 30 min | — |

### Commits à deux

Pour garder le `Co-authored-by:` sans le retaper à chaque fois, vous pouvez
activer le template de commit pour ce dépôt :

```bash
git config commit.template .gitmessage
```

Ensuite, chaque `git commit` dans ce projet ouvre un message prérempli avec la
ligne `Co-authored-by:` à compléter avec le binôme. Si vous voulez le même
comportement partout, ajoutez `--global`.

> ⏱️ **Le jalon qui compte** : vos 3 services doivent démarrer **avant
> d'attaquer la CI**. Si la tâche 3 n'est pas verte à 14h05, appelez —
> la tâche 5 est la plus longue des deux jours, elle ne se rattrape pas.

### M5-B2 — l'async individuel (jeudi + vendredi matin, 6 h)

Vous repartez **chacun·e** du repo binôme, dans une branche perso
`<prenom>/m5-b2-eval-continue`. Pas de nouveau repo.

| Quand | Étape | Durée | Appui |
|---|---|---|---|
| Jeudi | 1. **Préparation du jeu de référence** — récupérer le holdout M1, en tirer **votre** `data/reference_set.csv` (~500 lignes), puis geler le golden run (`--freeze-baseline`) | 30 min | [`data/README.md`](./data/README.md) + [`08_Evaluation_continue_seuils`](./ressources/08_Evaluation_continue_seuils_essentiel.md) |
| Jeudi | 2. `scripts/evaluate_model.py` + tracking **MLflow** (4 métriques, code retour 0 / non-zéro) | 1h30 | [`07_MLflow_tracking`](./ressources/07_MLflow_tracking_essentiel.md) + [`08`](./ressources/08_Evaluation_continue_seuils_essentiel.md) |
| Jeudi | 3. Définition et **justification** des seuils (`evaluation_thresholds.md`) | 1h | [`08_Evaluation_continue_seuils`](./ressources/08_Evaluation_continue_seuils_essentiel.md) |
| Vendredi | 4. Étape `evaluate-model` bloquante dans le workflow GitHub Actions | 1h | [`03_GitHub_Actions`](./ressources/03_GitHub_Actions_CI_CD_essentiel.md) |
| Vendredi | 5. Tests pytest pour l'évaluation | 45 min | [`03_GitHub_Actions`](./ressources/03_GitHub_Actions_CI_CD_essentiel.md) |
| Vendredi | 6. ⭐ Alerte Discord webhook (**bonus**) | 30 min | — |
| Vendredi | 7. Doc + merge | 45 min | — |

> ⚠️ **Le piège central de B2** : votre jeu de référence n'existe pas encore,
> et le fichier `data/reference_set_TEMPLATE.csv` du repo n'en est **pas** un
> (20 lignes = un exemple de format). C'est vous qui le construisez à partir du
> holdout M1, et sa composition est une **décision à argumenter**.
> Mode d'emploi : [`data/README.md`](./data/README.md).

### ✅ Checklist livrables

**M5-B1 — avant mercredi 12h30**

- [x] `docker compose up --build` démarre les **3 services** de façon **reproductible**, healthchecks verts
- [x] `/metrics` exposé côté `model` **et** `backend`
- [x] Dashboard Grafana provisionné **automatiquement** (3 panels : vie / vitesse / comportement)
- [x] Workflow CI **vert**, image poussée sur GHCR, tag `v1.0.0-prod`
- [x] Le **contract test** du modèle bloque la release s'il est rouge
      *(il vérifie le **contrat technique** de l'API — pas la performance du
      modèle : ça, c'est l'évaluation continue de B2)*
- [x] `runbook.md` — 4 procédures (Service KO / Latence / Métrique modèle / Rollback)
- [x] `README.md` — schéma Mermaid de l'archi + démarrage en 3 commandes
- [x] Commits binôme : `Co-authored-by:` ou auteurs nominatifs

**M5-B2 — avant vendredi 17h**

- [x] `data/reference_set.csv` (~500 lignes) **construit par vous** depuis le holdout M1, figé, versionné
- [x] `data/reference_baseline.json` — le golden run, gelé sur **ce** jeu
- [x] `scripts/evaluate_model.py` — 4 métriques, ≥ 2 runs MLflow comparables
- [x] `evaluation_thresholds.md` — 4 métriques × golden run / plancher absolu / baisse max / **justification**, tolérance relative ≥ 2 σ (bootstrap)
- [x] Étape `evaluate-model` dans la CI : `--degrade` fait **échouer** la release
      *(`mlruns/` est gitignoré : la preuve passe par l'**artefact CI**, pas par un commit)*

---

## 🚀 Démarrage (le service `model` tourne déjà)

```bash
# 1. Environnement de tests local (optionnel mais conseillé)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Vérifier que la base fournie passe les tests
pytest -v services/model/tests

# 3. Lancer ce qui est déjà câblé (model + prometheus + grafana)
docker compose up --build
```

> 🧰 **Avec `uv`** : `uv venv && source .venv/bin/activate` puis
> **`uv pip install -r requirements-dev.txt`**.
> ⚠️ Un venv créé par `uv venv` **n'embarque pas `pip`** : si vous voyez
> `No module named pip`, c'est ça — utilisez `uv pip install`, pas `pip install`.

> ⚠️ **Ports hôte** : frontend **8088** (pas 8080), Grafana **3001** (pas 3000)
> — pour éviter les conflits courants. Model 8000, backend 8001, Prometheus 9090.

Au départ, seuls `model`, `prometheus` et `grafana` démarrent : à vous
d'ajouter `backend` + `frontend` et de compléter le reste (cf. TODO).

---

## 📁 Structure

```
services/
  model/        # FOURNI — API scoring M1-B2 + /metrics (ne pas réécrire)
  backend/      # À COMPLÉTER — orchestrateur (tâche 2)
  frontend/     # À COMPLÉTER — formulaire nginx (tâche 2)
prometheus/     # FOURNI — scrape config
grafana/provisioning/
  datasources/  # FOURNI — datasource Prometheus
  dashboards/   # provider fourni ; le dashboard JSON = à vous (tâche 9)
.github/workflows/ci.yml   # squelette (job test fourni) — tâche 5
runbook.md                 # template 4 sections — tâche 10
data/README.md                       # B2 — d'où vient votre jeu de référence
data/reference_set_TEMPLATE.csv      # B2 — exemple de FORMAT (20 lignes), pas un jeu
scripts/evaluate_model_TEMPLATE.py   # B2 — MLflow pré-câblé
evaluation_thresholds_TEMPLATE.md    # B2 — seuils à justifier
ressources/                # 📚 mini-cours d'appui (lecture juste-à-temps)
```

> Le service `model` (déjà fourni) est votre **exemple de référence** : il
> expose déjà `/metrics` — répliquez ce pattern sur le `backend`.

---

## 📈 Évaluation continue (M5-B2)

Cette partie est implémentée et sert de garde-fou release contre les
régressions silencieuses du modèle.

### Artifacts versionnés

- `data/reference_set.csv` : jeu de référence figé (~500 lignes).
- `data/reference_baseline.json` : golden run mesuré sur ce jeu.
- `scripts/evaluate_model.py` : évalue, trace MLflow, compare aux seuils,
  retourne `0` (OK) ou `1` (blocage).
- `scripts/bootstrap_tolerance.py` : mesure le bruit bootstrap (σ, 2σ).
- `evaluation_thresholds.md` : choix des seuils et justifications.
- `tests/test_evaluation.py` : tests pytest dédiés à l'évaluation continue.

### Principe de comparaison

La CI compare la release courante au **golden run** (`data/reference_baseline.json`),
jamais à `metrics_holdout` de M1.

Pourquoi : le holdout M1 et le jeu de référence n'ont pas la même population.
Comparer les deux mesurerait un écart de population, pas une dégradation du modèle.

### Commandes utiles

```bash
# 1) (Une fois) geler le golden run si besoin
python scripts/evaluate_model.py --freeze-baseline

# 2) Run de release normal (doit sortir 0 si pas de dégradation)
python scripts/evaluate_model.py --release-tag v2.0.0

# 3) Test du chemin rouge (doit sortir non-zéro)
python scripts/evaluate_model.py --release-tag bad --degrade

# 4) Mesurer le bruit de mesure pour calibrer les tolérances
python scripts/bootstrap_tolerance.py --n-bootstrap 1000 --seed 42

# 5) Visualiser les runs
mlflow ui
```

### Afficher MLflow

Depuis la racine du projet, lancer l'interface MLflow locale :

```bash
py -3.12 -m mlflow ui --backend-store-uri ./mlruns
```

Puis ouvrir dans le navigateur :

```text
http://127.0.0.1:5000
```

Dans l'UI, aller dans l'expérience `pyrenex-eval-continue` pour comparer les runs.

Ce qu'on y retrouve pour chaque release :

- `Params` : `model_version`, `release_tag`, `reference_set`, `dataset_sha256`, hyperparamètres `hp_*`.
- `Metrics` : `f1_macro`, `f1_default`, `roc_auc`, `recall_default`.
- `Tags` : `release_blocked`.

Si l'écran est vide :

1. exécuter un run local, par exemple `py -3.12 scripts/evaluate_model.py --release-tag local-check`
2. relancer `py -3.12 -m mlflow ui --backend-store-uri ./mlruns`

Note environnement : sur cette machine, préférer `py -3.12` au `.venv` local si celui-ci est en Python 3.14, pour rester compatible avec les dépendances du modèle.

### Seuils et bruit de mesure

Stratégie retenue : **hybride** (plancher absolu + baisse max vs golden run).

Les tolérances relatives sont dimensionnées avec le bootstrap et respectent
la règle `tolérance >= 2σ` (voir `evaluation_thresholds.md`).

### Intégration CI/CD

Dans `.github/workflows/ci.yml` :

- job `evaluate-model` exécuté **après** les tests, **avant** le build,
- exécution normale de `scripts/evaluate_model.py` (gate release),
- smoke test volontaire `--degrade` qui doit échouer, pour prouver que le
  chemin rouge bloque réellement.

### Tests d'évaluation

`tests/test_evaluation.py` vérifie :

- run nominal => code retour `0`, pas de violation,
- run `--degrade` => code retour non-zéro, violations présentes,
- baseline manquante => message explicite demandant `--freeze-baseline`.

Ces tests sont branchés dans le workflow GitHub Actions.

## 📚 Ressources

Voir [`./ressources/`](./ressources/) — 8 mini-cours + `liens_officiels.md`.
Lecture **juste-à-temps** : ouvrez le mini-cours de la tâche en cours.

---

## 🆘 Bloqué·e·s ?

1. Relisez le mini-cours de la tâche en cours (`ressources/`).
2. Le service `model` est votre exemple qui marche : copiez ses patterns.
3. 30 min sur un bloquant → Discord `fil-M5`.