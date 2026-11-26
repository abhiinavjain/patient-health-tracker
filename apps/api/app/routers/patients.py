from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from .. import audit
from ..catalog import OBSERVATIONS
from ..deps import DB, CurrentUser, PatientCtx, require_roles
from ..models import AccessGrant, Appointment, Encounter, Patient, User
from ..schemas import (
    AllergyOut, AppointmentOut, ConditionOut, EncounterSummary, LatestObservation, MedicationOut,
    ObservationPoint, ObservationSeries, PatientCreate, PatientListItem, PatientOut, PatientSummary,
    PatientUpdate, TimelineEvent,
)
from ..services.risk import latest_scores
from .common import age_on, new_mrn, patient_out

router = APIRouter(tags=["patients"])


@router.get("/patients", response_model=list[PatientListItem])
def list_patients(user: CurrentUser, db: DB, q: str | None = None,
                  limit: int = Query(50, le=200), offset: int = 0):
    """Clinicians see patients who granted them access; a patient sees their own record."""
    stmt = select(Patient)
    if user.role == "clinician":
        stmt = stmt.join(AccessGrant, AccessGrant.patient_id == Patient.id).where(
            AccessGrant.clinician_id == user.id, AccessGrant.revoked_at.is_(None))
    elif user.role == "patient":
        stmt = stmt.where(Patient.user_id == user.id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins use aggregate analytics, not individual records")
    if q:
        stmt = stmt.where(Patient.full_name.ilike(f"%{q}%") | Patient.mrn.ilike(f"%{q}%"))
    patients = db.scalars(stmt.distinct().order_by(Patient.full_name).limit(limit).offset(offset)).all()
    ids = [p.id for p in patients]
    last = dict(db.execute(select(Encounter.patient_id, func.max(Encounter.started_at))
                           .where(Encounter.patient_id.in_(ids)).group_by(Encounter.patient_id)).all()) if ids else {}
    risks = latest_scores(db, ids)
    return [PatientListItem(
        id=p.id, mrn=p.mrn, full_name=p.full_name, date_of_birth=p.date_of_birth, sex=p.sex,
        age=age_on(p.date_of_birth), last_encounter_at=last.get(p.id),
        latest_risk={m: r.band for m, r in risks.get(p.id, {}).items()},
    ) for p in patients]


@router.post("/patients", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, db: DB, user: User = Depends(require_roles("clinician"))):
    """Register a walk-in patient. The registering clinician is granted access automatically."""
    p = Patient(mrn=new_mrn(db), created_by=user.id, **body.model_dump())
    db.add(p)
    db.flush()
    db.add(AccessGrant(patient_id=p.id, clinician_id=user.id, granted_by=user.id))
    audit.record(db, user, "create", patient_id=p.id, entity="patient", entity_id=p.id)
    db.commit()
    return patient_out(p)


@router.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(ctx: PatientCtx):
    audit.record(ctx.db, ctx.user, "view", patient_id=ctx.patient.id, entity="patient", entity_id=ctx.patient.id)
    ctx.db.commit()
    return patient_out(ctx.patient)


@router.patch("/patients/{patient_id}", response_model=PatientOut)
def update_patient(body: PatientUpdate, ctx: PatientCtx):
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(ctx.patient, k, v)
    audit.record(ctx.db, ctx.user, "update", patient_id=ctx.patient.id, entity="patient", entity_id=ctx.patient.id,
                 detail={"fields": sorted(changes)})
    ctx.db.commit()
    return patient_out(ctx.patient)


def _encounter_summary(e: Encounter) -> EncounterSummary:
    s = EncounterSummary.model_validate(e)
    s.diagnoses = [f"{c.icd10_code} {c.description}" for c in sorted(e.conditions, key=lambda c: not c.is_primary)]
    return s


@router.get("/patients/{patient_id}/summary", response_model=PatientSummary)
def summary(ctx: PatientCtx):
    """Everything a clinician needs at a glance: problems, meds, allergies, latest vitals/labs, next visit."""
    p, db = ctx.patient, ctx.db
    latest: dict[str, LatestObservation] = {}
    for o in sorted(p.observations, key=lambda o: o.observed_at):
        latest[o.code] = LatestObservation(code=o.code, label=OBSERVATIONS.get(o.code, (o.code,))[0],
                                           value=o.value, unit=o.unit, observed_at=o.observed_at)
    upcoming = db.scalars(select(Appointment).where(
        Appointment.patient_id == p.id, Appointment.status == "scheduled",
        Appointment.starts_at >= datetime.now(timezone.utc)).order_by(Appointment.starts_at).limit(3)).all()
    encounters = sorted(p.encounters, key=lambda e: e.started_at)
    audit.record(db, ctx.user, "view", patient_id=p.id, entity="summary")
    db.commit()
    return PatientSummary(
        patient=patient_out(p),
        active_conditions=[ConditionOut.model_validate(c) for c in p.conditions
                           if c.status == "active" and c.category == "problem"],
        active_medications=[MedicationOut.model_validate(m) for m in p.medications if m.status == "active"],
        allergies=[AllergyOut.model_validate(a) for a in p.allergies],
        latest_observations=sorted(latest.values(), key=lambda o: o.code),
        last_encounter=_encounter_summary(encounters[-1]) if encounters else None,
        upcoming_appointments=[AppointmentOut.model_validate(a) for a in upcoming],
        encounter_count=len(encounters),
    )


@router.get("/patients/{patient_id}/timeline", response_model=list[TimelineEvent])
def timeline(ctx: PatientCtx, limit: int = Query(200, le=1000)):
    """Chronological health history, newest first. Observations are summarised per encounter."""
    p = ctx.patient
    events: list[TimelineEvent] = []
    for e in p.encounters:
        clin = f" with {e.clinician.full_name}" if e.clinician else ""
        n_obs = len(e.observations)
        detail = "; ".join(filter(None, [
            e.reason,
            ", ".join(c.description for c in e.conditions) or None,
            f"{n_obs} measurement{'s' if n_obs != 1 else ''}" if n_obs else None,
        ]))
        events.append(TimelineEvent(at=e.started_at, kind="encounter", title=f"{e.type.title()} visit{clin}",
                                    detail=detail or None, encounter_id=e.id, ref_id=e.id))
    for c in p.conditions:
        if c.category != "problem":  # visit-only codes are already listed on the encounter event
            continue
        verb = "Diagnosed" if c.status == "active" else "Resolved"
        events.append(TimelineEvent(at=c.created_at, kind="condition", title=f"{verb}: {c.description}",
                                    detail=c.icd10_code, encounter_id=c.encounter_id, ref_id=c.id))
    for m in p.medications:
        label = m.action.replace("_", " ").capitalize()
        events.append(TimelineEvent(at=m.created_at, kind="medication", title=f"{label}: {m.name}",
                                    detail=" ".join(filter(None, [m.dose, m.frequency])) or None,
                                    encounter_id=m.encounter_id, ref_id=m.id))
    for o in p.observations:
        if o.encounter_id is None:  # self-reported readings; encounter readings are summarised above
            label = OBSERVATIONS.get(o.code, (o.code,))[0]
            events.append(TimelineEvent(at=o.observed_at, kind="observation", title=f"{label}: {o.value:g} {o.unit}",
                                        detail=f"Recorded by {o.source}", ref_id=o.id))
    for a in p.allergies:
        events.append(TimelineEvent(at=a.created_at, kind="allergy", title=f"Allergy: {a.substance}",
                                    detail=" — ".join(filter(None, [a.severity, a.reaction])), ref_id=a.id))

    def key(ev: TimelineEvent):
        at = ev.at if ev.at.tzinfo else ev.at.replace(tzinfo=timezone.utc)
        return at

    events.sort(key=key, reverse=True)
    audit.record(ctx.db, ctx.user, "view", patient_id=p.id, entity="timeline")
    ctx.db.commit()
    return events[:limit]


@router.get("/patients/{patient_id}/observations/series", response_model=list[ObservationSeries])
def observation_series(ctx: PatientCtx, codes: str = Query(..., description="Comma-separated, e.g. bp_systolic,bp_diastolic")):
    """Time series for trend charts."""
    wanted = [c.strip() for c in codes.split(",") if c.strip()]
    unknown = [c for c in wanted if c not in OBSERVATIONS]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown codes: {unknown}")
    out = []
    for code in wanted:
        rows = sorted((o for o in ctx.patient.observations if o.code == code), key=lambda o: o.observed_at)
        label, unit, _ = OBSERVATIONS[code]
        out.append(ObservationSeries(code=code, label=label, unit=unit, points=[
            ObservationPoint(observed_at=o.observed_at, value=o.value, source=o.source) for o in rows]))
    return out
