from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from .. import audit
from ..deps import DB, require_roles
from ..models import AuditLog, User
from ..schemas import AuditOut, StaffCreate, UserOut
from ..security import hash_password
from .auth import user_out

router = APIRouter(prefix="/admin", tags=["admin"])
Admin = Depends(require_roles("admin"))


class UserStatus(BaseModel):
    is_active: bool


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(body: StaffCreate, db: DB, admin: User = Admin):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    u = User(email=email, full_name=body.full_name, role=body.role, specialty=body.specialty,
             password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    audit.record(db, admin, "create", entity="user", entity_id=u.id, detail={"role": u.role})
    db.commit()
    return user_out(u)


@router.get("/users", response_model=list[UserOut])
def list_users(db: DB, _: User = Admin, role: str | None = None, limit: int = Query(100, le=500), offset: int = 0):
    stmt = select(User).order_by(User.role, User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    return [user_out(u) for u in db.scalars(stmt.limit(limit).offset(offset)).all()]


@router.patch("/users/{user_id}", response_model=UserOut)
def set_status(user_id: uuid.UUID, body: UserStatus, db: DB, admin: User = Admin):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if u.id == admin.id and not body.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    u.is_active = body.is_active
    audit.record(db, admin, "update", entity="user", entity_id=u.id, detail={"is_active": u.is_active})
    db.commit()
    return user_out(u)


@router.get("/audit", response_model=list[AuditOut])
def audit_log(db: DB, _: User = Admin, patient_id: uuid.UUID | None = None, actor_id: uuid.UUID | None = None,
              action: str | None = None, limit: int = Query(200, le=1000)):
    stmt = select(AuditLog).order_by(AuditLog.at.desc())
    if patient_id:
        stmt = stmt.where(AuditLog.patient_id == patient_id)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = db.scalars(stmt.limit(limit)).all()
    return [AuditOut(at=r.at, actor_name=r.actor.full_name if r.actor else None, actor_role=r.actor_role,
                     action=r.action, patient_id=r.patient_id, entity=r.entity, entity_id=r.entity_id) for r in rows]
