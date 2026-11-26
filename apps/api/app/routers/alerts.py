"""Acute alerts: clinicians review and optionally release them; patients see only released alerts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from .. import audit
from ..deps import DB, PatientCtx, require_roles
from ..models import AccessGrant, Alert, Patient, User
from ..schemas import AlertOut, AlertReview

router = APIRouter(tags=["alerts"])


def alert_out(a: Alert, patient_name: str | None = None) -> AlertOut:
    out = AlertOut.model_validate(a)
    out.reviewer_name = a.reviewer.full_name if a.reviewer else None
    out.patient_name = patient_name
    return out


@router.get("/patients/{patient_id}/alerts", response_model=list[AlertOut])
def patient_alerts(ctx: PatientCtx, open_only: bool = False):
    stmt = select(Alert).where(Alert.patient_id == ctx.patient.id).order_by(Alert.created_at.desc()).limit(50)
    if ctx.user.role == "patient":
        stmt = stmt.where(Alert.released_to_patient.is_(True))
    elif open_only:
        stmt = stmt.where(Alert.reviewed_at.is_(None))
    return [alert_out(a) for a in ctx.db.scalars(stmt).all()]


@router.post("/patients/{patient_id}/alerts/{alert_id}/review", response_model=AlertOut)
def review(alert_id: uuid.UUID, body: AlertReview, ctx: PatientCtx):
    ctx.require_clinician()
    a = ctx.db.get(Alert, alert_id)
    if a is None or a.patient_id != ctx.patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    a.reviewed_at, a.reviewed_by, a.review_note = datetime.now(timezone.utc), ctx.user.id, body.note
    a.released_to_patient = a.released_to_patient or body.release_to_patient
    audit.record(ctx.db, ctx.user, "review", patient_id=ctx.patient.id, entity="alert", entity_id=a.id,
                 detail={"level": a.level, "released": a.released_to_patient})
    ctx.db.commit()
    ctx.db.refresh(a)
    return alert_out(a)


@router.post("/patients/{patient_id}/alerts/{alert_id}/seen", response_model=AlertOut)
def seen(alert_id: uuid.UUID, ctx: PatientCtx):
    a = ctx.db.get(Alert, alert_id)
    if ctx.user.role != "patient" or a is None or a.patient_id != ctx.patient.id or not a.released_to_patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    a.patient_seen_at = a.patient_seen_at or datetime.now(timezone.utc)
    audit.record(ctx.db, ctx.user, "seen", patient_id=ctx.patient.id, entity="alert", entity_id=a.id)
    ctx.db.commit()
    return alert_out(a)


@router.get("/alerts", response_model=list[AlertOut])
def open_alerts(db: DB, user: User = Depends(require_roles("clinician"))):
    """Unreviewed alerts across the clinician's panel, most severe and newest first."""
    rows = db.execute(
        select(Alert, Patient.full_name).join(Patient, Patient.id == Alert.patient_id)
        .join(AccessGrant, AccessGrant.patient_id == Alert.patient_id)
        .where(AccessGrant.clinician_id == user.id, AccessGrant.revoked_at.is_(None), Alert.reviewed_at.is_(None))
        .order_by(Alert.created_at.desc()).limit(100)
    ).all()
    seen_ids, out = set(), []
    for a, name in rows:
        if a.id not in seen_ids:
            seen_ids.add(a.id)
            out.append(alert_out(a, name))
    rank = {"critical": 0, "urgent": 1, "watch": 2}
    return sorted(out, key=lambda x: rank[x.level])
