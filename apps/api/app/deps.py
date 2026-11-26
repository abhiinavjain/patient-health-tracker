"""Authentication and the access-control rules, in one place.

Who can see a patient's record:
  * the patient themself;
  * a clinician holding an active (un-revoked) AccessGrant for that patient;
  * NOT admins — admins manage accounts and see aggregate analytics and the audit log, but not
    individual charts (least privilege).
Clinical writes (encounters, diagnoses, medications…) require a clinician with access.
Patients may write their own lifestyle questionnaire and self-measured observations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import AccessGrant, Patient, User
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DB = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2)], db: DB) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
        return user

    return checker


def has_access(db: Session, user: User, patient: Patient) -> bool:
    if user.role == "patient":
        return patient.user_id == user.id
    if user.role == "clinician":
        return db.scalar(select(AccessGrant.id).where(
            AccessGrant.patient_id == patient.id,
            AccessGrant.clinician_id == user.id,
            AccessGrant.revoked_at.is_(None),
        ).limit(1)) is not None
    return False


@dataclass
class PatientContext:
    patient: Patient
    user: User
    db: Session

    @property
    def is_clinician(self) -> bool:
        return self.user.role == "clinician"

    def require_clinician(self) -> None:
        if not self.is_clinician:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a clinician with access can record clinical data")


def patient_context(patient_id: uuid.UUID, user: CurrentUser, db: DB) -> PatientContext:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    if not has_access(db, user, patient):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this patient's record")
    return PatientContext(patient=patient, user=user, db=db)


PatientCtx = Annotated[PatientContext, Depends(patient_context)]
