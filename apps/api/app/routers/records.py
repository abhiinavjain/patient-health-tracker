"""Problem list, medication list, allergies, lifestyle questionnaire and self-measured readings."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from .. import audit
from ..catalog import LAB_CODES
from ..deps import PatientCtx
from ..models import Allergy, Condition, LifestyleAssessment, Medication, Observation
from ..schemas import (
    AllergyIn, AllergyOut, ConditionOut, ConditionUpdate, LifestyleIn, LifestyleOut, MedicationIn, MedicationOut,
    ObservationIn, ObservationOut,
)
from ..services.risk import score_and_store

router = APIRouter(tags=["records"])


def _owned(ctx: PatientCtx, model, row_id: uuid.UUID):
    row = ctx.db.get(model, row_id)
    if row is None or row.patient_id != ctx.patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return row


# ----------------------------------------------------------------------------- conditions
@router.get("/patients/{patient_id}/conditions", response_model=list[ConditionOut])
def list_conditions(ctx: PatientCtx, status_: str | None = Query(None, alias="status")):
    rows = sorted(ctx.patient.conditions, key=lambda c: c.created_at, reverse=True)
    return [c for c in rows if status_ is None or c.status == status_]


@router.patch("/patients/{patient_id}/conditions/{condition_id}", response_model=ConditionOut)
def update_condition(condition_id: uuid.UUID, body: ConditionUpdate, ctx: PatientCtx):
    ctx.require_clinician()
    c = _owned(ctx, Condition, condition_id)
    c.status = body.status
    c.resolved_date = (body.resolved_date or date.today()) if body.status == "resolved" else None
    audit.record(ctx.db, ctx.user, "update", patient_id=ctx.patient.id, entity="condition", entity_id=c.id,
                 detail={"status": c.status})
    ctx.db.commit()
    return c


# ----------------------------------------------------------------------------- medications
@router.get("/patients/{patient_id}/medications", response_model=list[MedicationOut])
def list_medications(ctx: PatientCtx, status_: str | None = Query(None, alias="status")):
    rows = sorted(ctx.patient.medications, key=lambda m: m.created_at, reverse=True)
    return [m for m in rows if status_ is None or m.status == status_]


@router.post("/patients/{patient_id}/medications", response_model=MedicationOut, status_code=status.HTTP_201_CREATED)
def add_medication(body: MedicationIn, ctx: PatientCtx):
    ctx.require_clinician()
    m = Medication(patient_id=ctx.patient.id, start_date=body.start_date or date.today(), status="active",
                   **body.model_dump(exclude={"start_date"}))
    ctx.db.add(m)
    ctx.db.flush()
    audit.record(ctx.db, ctx.user, "create", patient_id=ctx.patient.id, entity="medication", entity_id=m.id)
    ctx.db.commit()
    return m


@router.post("/patients/{patient_id}/medications/{medication_id}/stop", response_model=MedicationOut)
def stop_medication(medication_id: uuid.UUID, ctx: PatientCtx):
    ctx.require_clinician()
    m = _owned(ctx, Medication, medication_id)
    m.status, m.end_date = "stopped", date.today()
    audit.record(ctx.db, ctx.user, "update", patient_id=ctx.patient.id, entity="medication", entity_id=m.id,
                 detail={"status": "stopped"})
    ctx.db.commit()
    return m


# ----------------------------------------------------------------------------- allergies
@router.get("/patients/{patient_id}/allergies", response_model=list[AllergyOut])
def list_allergies(ctx: PatientCtx):
    return ctx.patient.allergies


@router.post("/patients/{patient_id}/allergies", response_model=AllergyOut, status_code=status.HTTP_201_CREATED)
def add_allergy(body: AllergyIn, ctx: PatientCtx):
    """Clinicians and patients may both record allergies (patient-reported allergies matter for safety)."""
    a = Allergy(patient_id=ctx.patient.id, **body.model_dump())
    ctx.db.add(a)
    ctx.db.flush()
    audit.record(ctx.db, ctx.user, "create", patient_id=ctx.patient.id, entity="allergy", entity_id=a.id)
    ctx.db.commit()
    return a


# ----------------------------------------------------------------------------- lifestyle questionnaire
@router.get("/patients/{patient_id}/lifestyle", response_model=list[LifestyleOut])
def list_lifestyle(ctx: PatientCtx):
    return list(reversed(ctx.patient.lifestyle))


@router.post("/patients/{patient_id}/lifestyle", response_model=LifestyleOut, status_code=status.HTTP_201_CREATED)
def add_lifestyle(body: LifestyleIn, ctx: PatientCtx):
    row = LifestyleAssessment(patient_id=ctx.patient.id, **body.model_dump())
    ctx.db.add(row)
    ctx.db.flush()
    audit.record(ctx.db, ctx.user, "create", patient_id=ctx.patient.id, entity="lifestyle", entity_id=row.id)
    ctx.db.refresh(ctx.patient)
    score_and_store(ctx.db, ctx.patient)
    ctx.db.commit()
    return row


# ----------------------------------------------------------------------------- observations
@router.post("/patients/{patient_id}/observations", response_model=ObservationOut, status_code=status.HTTP_201_CREATED)
def add_observation(body: ObservationIn, ctx: PatientCtx):
    """Standalone reading outside a visit, e.g. a home BP or weight. Patients cannot enter lab results."""
    source = "clinician" if ctx.is_clinician else "patient"
    if source == "patient" and body.code in LAB_CODES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Lab results must be entered by a clinician")
    o = Observation(patient_id=ctx.patient.id, code=body.code, value=body.value, unit=body.unit,
                    observed_at=body.observed_at or datetime.now(timezone.utc), source=source)
    ctx.db.add(o)
    ctx.db.flush()
    audit.record(ctx.db, ctx.user, "create", patient_id=ctx.patient.id, entity="observation", entity_id=o.id)
    ctx.db.commit()
    return o
