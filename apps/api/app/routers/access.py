"""Patient-controlled consent: grant/revoke clinician access, and see who looked at the record."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from .. import audit
from ..deps import PatientContext, PatientCtx
from ..models import AccessGrant, AuditLog, User
from ..schemas import AuditOut, GrantIn, GrantOut

router = APIRouter(tags=["access"])


def _require_owner(ctx: PatientContext) -> None:
    if ctx.user.role != "patient":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient can manage access to their record")


def grant_access(db, patient_id: uuid.UUID, clinician: User, actor: User, reason: str | None = None) -> AccessGrant:
    existing = db.scalar(select(AccessGrant).where(
        AccessGrant.patient_id == patient_id, AccessGrant.clinician_id == clinician.id,
        AccessGrant.revoked_at.is_(None)))
    if existing:
        return existing
    g = AccessGrant(patient_id=patient_id, clinician_id=clinician.id, granted_by=actor.id)
    db.add(g)
    db.flush()
    audit.record(db, actor, "grant", patient_id=patient_id, entity="access_grant", entity_id=g.id,
                 detail={"clinician_id": str(clinician.id), **({"reason": reason} if reason else {})})
    return g


@router.get("/patients/{patient_id}/access", response_model=list[GrantOut])
def list_grants(ctx: PatientCtx, include_revoked: bool = False):
    _require_owner(ctx)
    stmt = select(AccessGrant).where(AccessGrant.patient_id == ctx.patient.id).order_by(AccessGrant.granted_at.desc())
    if not include_revoked:
        stmt = stmt.where(AccessGrant.revoked_at.is_(None))
    return ctx.db.scalars(stmt).all()


@router.post("/patients/{patient_id}/access", response_model=GrantOut, status_code=status.HTTP_201_CREATED)
def create_grant(body: GrantIn, ctx: PatientCtx):
    _require_owner(ctx)
    clinician = ctx.db.get(User, body.clinician_id)
    if clinician is None or clinician.role != "clinician" or not clinician.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinician not found")
    g = grant_access(ctx.db, ctx.patient.id, clinician, ctx.user)
    ctx.db.commit()
    return g


@router.delete("/patients/{patient_id}/access/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_grant(grant_id: uuid.UUID, ctx: PatientCtx):
    _require_owner(ctx)
    g = ctx.db.get(AccessGrant, grant_id)
    if g is None or g.patient_id != ctx.patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grant not found")
    if g.revoked_at is None:
        g.revoked_at = datetime.now(timezone.utc)
        audit.record(ctx.db, ctx.user, "revoke", patient_id=ctx.patient.id, entity="access_grant", entity_id=g.id,
                     detail={"clinician_id": str(g.clinician_id)})
        ctx.db.commit()


@router.get("/patients/{patient_id}/audit", response_model=list[AuditOut])
def record_access_log(ctx: PatientCtx, limit: int = Query(100, le=500)):
    """'Who has looked at my record?' — every view and change, newest first."""
    _require_owner(ctx)
    rows = ctx.db.scalars(select(AuditLog).where(AuditLog.patient_id == ctx.patient.id)
                          .order_by(AuditLog.at.desc()).limit(limit)).all()
    return [AuditOut(at=r.at, actor_name=r.actor.full_name if r.actor else None, actor_role=r.actor_role,
                     action=r.action, patient_id=r.patient_id, entity=r.entity, entity_id=r.entity_id) for r in rows]
