from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import audit
from ..deps import CurrentUser, PatientCtx
from ..models import RiskScore
from ..schemas import RiskHistoryPoint, RiskResult
from ..services.risk import MODEL_NAMES, available_models, score_and_store, score_patient

router = APIRouter(tags=["risk"])


@router.get("/risk/models")
def models(_: CurrentUser):
    """Model registry: version, intended use and headline test metrics (for 'about this score' panels)."""
    out = []
    for m in available_models():
        md = m.metadata
        test = md["metrics"]["test"]
        out.append({
            "name": md["name"], "title": md["title"], "version": md["version"], "trained_at": md["trained_at"],
            "target": md["target"], "intended_use": m.task.intended_use, "limitations": m.task.limitations,
            "metrics": {k: test[k] for k in ("roc_auc", "roc_auc_ci95", "pr_auc", "brier", "prevalence")},
            "risk_bands": md["risk_bands"], "top_k": md["top_k"],
        })
    return out


@router.get("/patients/{patient_id}/risk", response_model=list[RiskResult])
def current_risk(ctx: PatientCtx):
    """Live scores from the current record (not persisted — cheap to compute, always up to date)."""
    results = score_patient(ctx.patient)
    audit.record(ctx.db, ctx.user, "view", patient_id=ctx.patient.id, entity="risk")
    ctx.db.commit()
    return results


@router.post("/patients/{patient_id}/risk/recompute", response_model=list[RiskResult])
def recompute(ctx: PatientCtx):
    """Score and store a snapshot (also happens automatically after each encounter / questionnaire)."""
    results = score_and_store(ctx.db, ctx.patient)
    audit.record(ctx.db, ctx.user, "risk", patient_id=ctx.patient.id, entity="risk")
    ctx.db.commit()
    return results


@router.get("/patients/{patient_id}/risk/{model}/history", response_model=list[RiskHistoryPoint])
def history(model: str, ctx: PatientCtx):
    if model not in MODEL_NAMES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown model")
    rows = ctx.db.scalars(select(RiskScore).where(RiskScore.patient_id == ctx.patient.id, RiskScore.model == model)
                          .order_by(RiskScore.computed_at)).all()
    return [RiskHistoryPoint(computed_at=r.computed_at, score=r.score, band=r.band, model_version=r.model_version)
            for r in rows]
