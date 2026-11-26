from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from .config import get_settings

_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _hasher.verify(password, hashed)


def _encode(sub: uuid.UUID, role: str, kind: str, ttl: timedelta) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(sub), "role": role, "type": kind, "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def create_tokens(user_id: uuid.UUID, role: str) -> dict:
    s = get_settings()
    return {
        "access_token": _encode(user_id, role, "access", timedelta(minutes=s.access_token_minutes)),
        "refresh_token": _encode(user_id, role, "refresh", timedelta(days=s.refresh_token_days)),
        "token_type": "bearer",
        "expires_in": s.access_token_minutes * 60,
    }


def decode_token(token: str, expected_type: str) -> dict:
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload
