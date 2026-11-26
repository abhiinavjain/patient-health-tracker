"""Tests run against an in-memory SQLite database and the real trained model artifacts."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "test-password-123"


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(Session):
    app = create_app()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c


class Actor:
    def __init__(self, client: TestClient, email: str, user_id: str, patient_id: str | None = None):
        self.client, self.email, self.id, self.patient_id = client, email, user_id, patient_id
        r = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def get(self, url, **kw):
        return self.client.get(f"/api/v1{url}", headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(f"/api/v1{url}", headers=self.headers, **kw)

    def patch(self, url, **kw):
        return self.client.patch(f"/api/v1{url}", headers=self.headers, **kw)

    def delete(self, url, **kw):
        return self.client.delete(f"/api/v1{url}", headers=self.headers, **kw)


def _staff(Session, client, email, role, specialty=None) -> Actor:
    db = Session()
    u = User(email=email, full_name=email.split("@")[0].title(), role=role, specialty=specialty,
             password_hash=hash_password(PASSWORD))
    db.add(u)
    db.commit()
    uid = str(u.id)
    db.close()
    return Actor(client, email, uid)


def signup(client, email, dob="1960-05-01", sex="female") -> Actor:
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PASSWORD, "full_name": "Test Patient",
                                                 "date_of_birth": dob, "sex": sex})
    assert r.status_code == 201, r.text
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    return Actor(client, email, me["id"], me["patient_id"])


@pytest.fixture
def admin(client, Session):
    return _staff(Session, client, "admin@test.pht", "admin")


@pytest.fixture
def doctor(client, Session):
    return _staff(Session, client, "doc@test.pht", "clinician", "Internal Medicine")


@pytest.fixture
def other_doctor(client, Session):
    return _staff(Session, client, "doc2@test.pht", "clinician", "Cardiology")


@pytest.fixture
def patient(client):
    return signup(client, "pat@test.pht")


@pytest.fixture
def granted(patient, doctor):
    """`patient` has granted `doctor` access."""
    r = patient.post(f"/patients/{patient.patient_id}/access", json={"clinician_id": doctor.id})
    assert r.status_code == 201, r.text
    return patient
