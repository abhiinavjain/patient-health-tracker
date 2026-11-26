"""Create Alert rows from new readings."""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from ..models import Alert, Patient, User
from .alerts import assess


def raise_alert(db: Session, patient: Patient, actor: User, encounter_id=None) -> Alert | None:
    """Assess the patient's current readings; store an alert if anything is off. Returns the alert or None."""
    a = assess(list(patient.observations))
    if a.level == "normal":
        return None
    alert = Alert(patient_id=patient.id, encounter_id=encounter_id, level=a.level, news2=a.news2,
                  reasons=[asdict(r) for r in a.reasons], source="patient" if actor.role == "patient" else "clinician",
                  created_by=actor.id)
    db.add(alert)
    db.flush()
    return alert
