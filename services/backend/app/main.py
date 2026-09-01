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

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

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

# TODO 1 — exposer /metrics avec prometheus-fastapi-instrumentator
#   (cf. service model). Pensez à une métrique métier : compteur d'erreurs
#   upstream lors de l'appel au model.


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
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{MODEL_URL}/predict", json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model service unreachable: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service returned an upstream error",
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected model response status: {response.status_code}",
        )

    try:
        body = response.json()
        return Prediction(**body)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid model response payload: {exc.__class__.__name__}",
        ) from exc
