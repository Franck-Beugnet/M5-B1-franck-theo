"""Service `backend` — orchestrateur (SQUELETTE À COMPLÉTER).

Rôle attendu : exposé au navigateur (via le frontend nginx), il valide
l'entrée avec le **même schéma Pydantic** que le modèle, appelle le service
`model` en interne (`http://model:8000/predict`), et expose `/health`,
`/score`, `/metrics`.

👉 Inspirez-vous du service `model` (déjà fourni) pour le pattern `/metrics`
   et le middleware de logging. Mini-cours : `02_FastAPI_metrics_Prometheus`.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from app.middleware import LoggingMiddleware
from app.schemas import HealthResponse, LoanApplication, Prediction

# URL du service model — configurable par variable d'env (dev/staging/prod)
MODEL_URL = os.environ.get("MODEL_URL", "http://model:8000")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8088").split(",")

app = FastAPI(title="Pyrenex Backend Orchestrator", version="1.0.0")
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

UPSTREAM_ERRORS = Counter(
    "pyrenex_backend_upstream_errors_total",
    "Number of upstream errors while calling model service",
    ["reason"],
)

SCORES_TOTAL = Counter(
    "pyrenex_backend_scores_total",
    "Nombre de scorings retournes par le backend, par classe predite.",
    ["predicted_class"],
)

SCORE_PROBA = Histogram(
    "pyrenex_backend_score_probability",
    "Distribution des probabilites de defaut retournees par le backend.",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

UPSTREAM_MODEL_LATENCY_SECONDS = Histogram(
    "pyrenex_backend_upstream_model_latency_seconds",
    "Latence de l'appel HTTP backend -> model /predict (secondes).",
    buckets=(0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

# Expose /metrics (latence, RPS, codes retour) + métrique métier custom.
Instrumentator(should_group_status_codes=False).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness du backend (ne dépend PAS du model)."""
    return HealthResponse(status="ok")

@app.post("/score", response_model=Prediction)
async def score(application: LoanApplication, request: Request) -> Prediction:
    """Valide l'entree puis orchestre un appel interne au service model."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get(
        "X-Request-ID", "n/a"
    )
    headers = {"X-Request-ID": request_id}
    payload = application.model_dump()

    try:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{MODEL_URL}/predict", json=payload, headers=headers)
        UPSTREAM_MODEL_LATENCY_SECONDS.observe(time.perf_counter() - start)
    except httpx.RequestError as exc:
        UPSTREAM_ERRORS.labels(reason="unreachable").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model service unreachable: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 500:
        UPSTREAM_ERRORS.labels(reason="upstream_5xx").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service returned an upstream error",
        )
    if response.status_code != status.HTTP_200_OK:
        UPSTREAM_ERRORS.labels(reason="unexpected_status").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected model response status: {response.status_code}",
        )

    try:
        body = response.json()
        prediction = Prediction(**body)
        SCORES_TOTAL.labels(predicted_class=str(prediction.prediction)).inc()
        SCORE_PROBA.observe(prediction.probability)
        return prediction
    except Exception as exc:  # noqa: BLE001
        UPSTREAM_ERRORS.labels(reason="invalid_payload").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid model response payload: {exc.__class__.__name__}",
        ) from exc
