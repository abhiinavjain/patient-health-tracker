from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from .. import audit
from ..deps import PatientCtx
from ..models import Condition, Encounter, Medication, Observation
from ..schemas import EncounterIn, EncounterOut, EncounterSummary
from ..services.risk import score_and_store
from .patients import _encounter_summary

router = APIRouter(tags=["encounters"])
log = logging.getLogger(__name__)


@router.post("/patients/{patient_id}/encounters", response_model=EncounterOut, status_code=status.HTTP_201_CREATED)
def record_encounter(body: EncounterIn, ctx: PatientCtx):
    """Record a consultation/admission and everything captured during it, in one transaction.

    This is how a patient's history gets updated after each doctor visit. Risk scores are recomputed afterwards.
    """
    ctx.require_clinician()
    p, db = ctx.patient, ctx.db
    enc = Encounter(patient_id=p.id, clinician_id=ctx.user.id,
                    **body.model_dump(exclude={"conditions", "observations", "medications", "stop_medication_ids"}))
    db.add(enc)
    db.flush()
    visit_day = body.started_at.date()

    for c in body.conditions:
        db.add(Condition(patient_id=p.id, encounter_id=enc.id, onset_date=c.onset_date or visit_day,
                         **c.model_dump(exclude={"onset_date"})))
    for o in body.observations:
        db.add(Observation(patient_id=p.id, encounter_id=enc.id, code=o.code, value=o.value, unit=o.unit,
                           observed_at=o.observed_at or body.started_at, source="clinician"))
    new_names = {m.name.strip().lower() for m in body.medications if m.action != "stopped"}
    for med in p.medications:  # starting/changing a drug that's already active replaces the old entry
        if med.status == "active" and med.name.strip().lower() in new_names:
            med.status, med.end_date = "stopped", visit_day
    for m in body.medications:
        db.add(Medication(patient_id=p.id, encounter_id=enc.id, start_date=m.start_date or visit_day,
                          status="stopped" if m.action == "stopped" else "active",
                          end_date=visit_day if m.action == "stopped" else None,
                          **m.model_dump(exclude={"start_date"})))
    for mid in body.stop_medication_ids:
        med = db.get(Medication, mid)
        if med is None or med.patient_id != p.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Medication {mid} not found for this patient")
        med.status, med.end_date = "stopped", visit_day
        db.add(Medication(patient_id=p.id, encounter_id=enc.id, name=med.name, dose=med.dose,
                          frequency=med.frequency, route=med.route, start_date=med.start_date, end_date=visit_day,
                          status="stopped", action="stopped"))

    audit.record(db, ctx.user, "create", patient_id=p.id, entity="encounter", entity_id=enc.id,
                 detail={"type": enc.type, "conditions": len(body.conditions), "observations": len(body.observations),
                         "medications": len(body.medications)})
    db.flush()
    db.refresh(p)
    try:
        score_and_store(db, p)
    except Exception:  # scoring must never block saving the clinical record
        log.exception("risk scoring failed for patient %s", p.id)
    db.commit()
    db.refresh(enc)
    return enc


@router.get("/patients/{patient_id}/encounters", response_model=list[EncounterSummary])
def list_encounters(ctx: PatientCtx, type: str | None = None):
    encs = sorted(ctx.patient.encounters, key=lambda e: e.started_at, reverse=True)
    return [_encounter_summary(e) for e in encs if type is None or e.type == type]


@router.get("/patients/{patient_id}/encounters/{encounter_id}", response_model=EncounterOut)
def get_encounter(encounter_id: uuid.UUID, ctx: PatientCtx):
    enc = ctx.db.get(Encounter, encounter_id)
    if enc is None or enc.patient_id != ctx.patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    audit.record(ctx.db, ctx.user, "view", patient_id=ctx.patient.id, entity="encounter", entity_id=enc.id)
    ctx.db.commit()
    return enc

