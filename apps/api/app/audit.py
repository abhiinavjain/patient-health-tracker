from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from .models import AuditLog, User


def record(db: Session, actor: User | None, action: str, *, patient_id: uuid.UUID | None = None,
           entity: str | None = None, entity_id: object = None, detail: dict | None = None) -> None:
    """Queue an audit entry in the caller's transaction (committed with the change it describes)."""
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        patient_id=patient_id,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
    ))
