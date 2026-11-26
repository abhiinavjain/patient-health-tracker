from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from .. import audit
from ..deps import DB, CurrentUser, PatientCtx, has_access
from ..models import Appointment, Patient, User
from ..schemas import AppointmentIn, AppointmentOut, AppointmentUpdate
from .access import grant_access

router = APIRouter(tags=["appointments"])


@router.post("/patients/{patient_id}/appointments", response_model=AppointmentOut,
             status_code=status.HTTP_201_CREATED)
def book(body: AppointmentIn, ctx: PatientCtx):
    """Book a visit. When a patient books, the clinician is granted access to their record (audited)."""
    clinician = ctx.db.get(User, body.clinician_id)
    if clinician is None or clinician.role != "clinician" or not clinician.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinician not found")
    if body.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Appointment must be in the future")
    if ctx.user.role == "patient":
        grant_access(ctx.db, ctx.patient.id, clinician, ctx.user, reason="appointment booked")
    a = Appointment(patient_id=ctx.patient.id, clinician_id=clinician.id, starts_at=body.starts_at, reason=body.reason)
    ctx.db.add(a)
    ctx.db.flush()
    audit.record(ctx.db, ctx.user, "create", patient_id=ctx.patient.id, entity="appointment", entity_id=a.id)
    ctx.db.commit()
    ctx.db.refresh(a)
    return a


@router.get("/appointments", response_model=list[AppointmentOut])
def my_appointments(user: CurrentUser, db: DB, days_ahead: int = Query(30, le=365), include_past: bool = False):
    """A patient's own appointments, or a clinician's schedule."""
    now = datetime.now(timezone.utc)
    stmt = select(Appointment).order_by(Appointment.starts_at)
    if user.role == "patient":
        stmt = stmt.join(Patient).where(Patient.user_id == user.id)
    elif user.role == "clinician":
        stmt = stmt.where(Appointment.clinician_id == user.id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available for admins")
    if not include_past:
        stmt = stmt.where(Appointment.starts_at >= now - timedelta(hours=12))
    stmt = stmt.where(Appointment.starts_at <= now + timedelta(days=days_ahead))
    return db.scalars(stmt).all()


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: uuid.UUID, body: AppointmentUpdate, user: CurrentUser, db: DB):
    a = db.get(Appointment, appointment_id)
    patient = db.get(Patient, a.patient_id) if a else None
    if a is None or patient is None or not (a.clinician_id == user.id or has_access(db, user, patient)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    if user.role == "patient":
        if body.status not in (None, "cancelled") or body.starts_at is not None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients can only cancel; contact the clinic to reschedule")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(a, k, v)
    audit.record(db, user, "update", patient_id=a.patient_id, entity="appointment", entity_id=a.id,
                 detail={k: str(v) for k, v in changes.items()})
    db.commit()
    return a
