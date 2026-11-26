from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import access, admin, alerts, analytics, appointments, auth, encounters, notes, patients, records, risk
from .services.risk import available_models

log = logging.getLogger("pht")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loaded = available_models()  # warm the model cache so the first request isn't slow
    log.info("Loaded risk models: %s", [m.task.name for m in loaded])
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Patient Health Tracker API",
        version="2.0.0",
        description="Longitudinal patient records with consent-based access, audit logging and explainable "
                    "risk predictions. Demo system on synthetic data — not a medical device.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for r in (auth, patients, encounters, alerts, notes, records, access, appointments, risk, analytics, admin):
        app.include_router(r.router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "models": [m.task.name for m in available_models()]}

    return app


app = create_app()
