from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from .. import audit
from ..config import get_settings
from ..deps import DB, CurrentUser
from ..models import Patient, User
from ..schemas import ClinicianOut, PatientSignup, RefreshIn, Token, UserOut
from ..security import create_tokens, decode_token, hash_password, verify_password
from ..throttle import LoginThrottle
from .common import new_mrn

router = APIRouter(tags=["auth"])

# Verifying against a real hash when the user doesn't exist keeps response time similar (no user enumeration).
_DUMMY_HASH = hash_password("not-a-real-password-0000")
_settings = get_settings()
throttle = LoginThrottle(_settings.login_max_failures, _settings.login_window_minutes * 60)


def user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.patient_id = user.patient.id if user.patient else None
    return out


@router.post("/auth/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(body: PatientSignup, db: DB):
    """Patients create their own account and an empty health record."""
    if not get_settings().allow_patient_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-registration is disabled")
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, full_name=body.full_name, role="patient", password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    patient = Patient(user_id=user.id, mrn=new_mrn(db), full_name=body.full_name, date_of_birth=body.date_of_birth,
                      sex=body.sex, phone=body.phone, created_by=user.id)
    db.add(patient)
    db.flush()
    audit.record(db, user, "signup", patient_id=patient.id, entity="patient", entity_id=patient.id)
    db.commit()
    return create_tokens(user.id, user.role)


@router.post("/auth/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    email = form.username.lower()
    wait = throttle.retry_after(email)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed sign-in attempts. Try again in {max(1, wait // 60)} minute(s).",
                            headers={"Retry-After": str(wait)})
    user = db.scalar(select(User).where(User.email == email))
    valid = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.is_active:
        throttle.failure(email)  # counted for unknown emails too, so lockouts don't reveal which accounts exist
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    throttle.success(email)
    audit.record(db, user, "login", entity="user", entity_id=user.id)
    db.commit()
    return create_tokens(user.id, user.role)


@router.post("/auth/refresh", response_model=Token)
def refresh(body: RefreshIn, db: DB):
    try:
        payload = decode_token(body.refresh_token, "refresh")
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return create_tokens(user.id, user.role)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return user_out(user)


@router.get("/clinicians", response_model=list[ClinicianOut])
def clinicians(_: CurrentUser, db: DB, q: str | None = None):
    """Directory used when granting access or booking an appointment."""
    stmt = select(User).where(User.role == "clinician", User.is_active.is_(True)).order_by(User.full_name)
    if q:
        stmt = stmt.where(User.full_name.ilike(f"%{q}%") | User.specialty.ilike(f"%{q}%"))
    return db.scalars(stmt.limit(100)).all()
