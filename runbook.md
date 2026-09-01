# Runbook d'astreinte — Pyrenex Prod

Objectif: permettre a une astreinte SRE non data de restaurer le service vite
et sans aggraver l'incident.

## 1. Service KO (un conteneur down)

**Declenchement**
- Panel Grafana "Vie - Service up (1=up, 0=down)" a 0 pour `model` ou `backend` pendant plus de 1 minute.
- Ou `docker compose ps` montre un service `Exit`/`Restarting`.

**Actions**
1. Identifier le service impacte: `docker compose ps`.
2. Lire la cause immediate: `docker compose logs --tail=200 model` ou `docker compose logs --tail=200 backend`.
3. Redemarrer uniquement le service KO: `docker compose restart model` ou `docker compose restart backend`.
4. Verifier le retour a la normale: `/health` repond 200 et panel "up" revient a 1.
5. Si toujours KO apres 2 redemarrages en 10 min, escalader.

**Qui appeler**
- T+0: SRE on-call (prise en charge).
- T+10 min: engineer backend/model on-call.
- T+20 min: incident manager si indisponibilite client.

**On NE fait PAS**
- Ne pas executer `docker compose down -v`.
- Ne pas redemarrer toute la stack sans diagnostic minimal.

## 2. Latence p95 degradee

**Declenchement**
- Panel "Vitesse - Latence model p50 p95 p99": p95 > 0.35 s pendant 5 minutes.
- Ou p99 > 0.80 s pendant 5 minutes.

**Actions**
1. Confirmer la charge: regarder "Vie - RPS par service".
2. Verifier saturation machine: `docker stats --no-stream`.
3. Verifier si erreurs en hausse: panel "Vie - Erreurs 5xx par service".
4. Si CPU/memoire saturee, redemarrer `model` en premier puis re-mesurer 5 min.
5. Si latence reste elevee sans saturation, preparer rollback (procedure 4).

**Qui appeler**
- T+0: SRE on-call.
- T+15 min: engineer model on-call.
- T+30 min: incident manager si SLO impacte.

**On NE fait PAS**
- Ne pas deployer un hotfix non teste en production.
- Ne pas modifier les seuils d'alerte pendant l'incident.

## 3. Comportement prediction anormal

**Declenchement**
- Panel "Comportement - Repartition des classes predites": la classe `1` double ou est divisee par 2 vs niveau habituel pendant 15 min.
- Ou panel "Comportement - Proba defaut p50 p95": p95 > 0.90 pendant 15 min.

**Actions**
1. Verifier d'abord la sante technique: panels "up", "RPS", "5xx".
2. Verifier les erreurs upstream backend: `pyrenex_backend_upstream_errors_total` doit rester stable.
3. Si technique saine, classer en suspicion de drift data (incident non bloquant infra).
4. Ouvrir ticket "Data/Model" avec heure de debut, captures dashboard, impact metier observe.
5. Renforcer surveillance (fenetre 1h) et preparer rollback uniquement si metier le demande.

**Qui appeler**
- T+0: SRE on-call.
- T+15 min: data scientist/model owner.
- T+30 min: product owner si decision metier requise.

**On NE fait PAS**
- Ne pas conclure "le modele est faux" sans verite terrain.
- Ne pas re-entrainer en urgence depuis la prod.

## 4. Rollback de release

**Declenchement**
- Incident post-release confirme: KO service > 10 min, ou latence/5xx hors seuil > 15 min apres tentative de remediation.
- Ou gate qualite rouge en CI sur la release candidate.

**Actions**
1. Identifier la derniere version stable (tag precedent `vX.Y.Z`).
2. Re-deployer l'image stable depuis GHCR.
3. Redemarrer uniquement les services impactes (`model`, puis `backend`).
4. Verifier retour vert: `/health`, panel up=1, p95 revenu sous seuil, 5xx proche de 0.
5. Consigner l'incident: heure, cause probable, action, resultat.

**Qui appeler**
- T+0: SRE on-call + release manager.
- T+15 min: engineer responsable du dernier changement.
- T+30 min: incident manager si impact client continue.

**On NE fait PAS**
- Ne pas supprimer les images/tags precedents pendant l'incident.
- Ne pas faire de rollback partiel non documente.
