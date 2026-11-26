from __future__ import annotations

import secrets
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Patient
from ..schemas import PatientOut


def age_on(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def new_mrn(db: Session) -> str:
    while True:
        mrn = f"PHT{secrets.randbelow(10**7):07d}"
        if db.scalar(select(Patient.id).where(Patient.mrn == mrn)) is None:
            return mrn


def patient_out(p: Patient) -> PatientOut:
    out = PatientOut.model_validate(p)
    out.age = age_on(p.date_of_birth)
    return out
