"""Relational model of a longitudinal health record (FHIR-inspired, simplified).

A consultation creates an Encounter; the Conditions, Observations and Medications recorded during it point
back to that Encounter. The patient's timeline is those rows ordered by time.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum(*values: str, name: str):
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


ROLES = ("patient", "clinician", "admin")
SEXES = ("female", "male", "other")
ENCOUNTER_TYPES = ("outpatient", "inpatient", "emergency", "telehealth")
ADMISSION_TYPES = ("emergency", "urgent", "elective")
ADMISSION_SOURCES = ("emergency_room", "referral", "transfer", "other")
DISPOSITIONS = ("home", "home_health", "facility", "left_ama", "expired", "other")
CONDITION_STATUS = ("active", "resolved")
CONDITION_CATEGORIES = ("problem", "encounter")
MED_STATUS = ("active", "stopped")
MED_ACTIONS = ("started", "continued", "dose_increased", "dose_decreased", "stopped")
OBS_SOURCES = ("clinician", "patient", "device")
SEVERITIES = ("mild", "moderate", "severe")
APPT_STATUS = ("scheduled", "completed", "cancelled", "no_show")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(_enum(*ROLES, name="user_role"))
    password_hash: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    patient: Mapped[Patient | None] = relationship(back_populates="user", foreign_keys="Patient.user_id")


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    mrn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(_enum(*SEXES, name="sex"))
    blood_group: Mapped[str | None] = mapped_column(String(5))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(300))
    emergency_contact: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    user: Mapped[User | None] = relationship(back_populates="patient", foreign_keys=[user_id])
    encounters: Mapped[list[Encounter]] = relationship(back_populates="patient", cascade="all, delete-orphan",
                                                       order_by="Encounter.started_at")
    conditions: Mapped[list[Condition]] = relationship(cascade="all, delete-orphan")
    observations: Mapped[list[Observation]] = relationship(cascade="all, delete-orphan")
    medications: Mapped[list[Medication]] = relationship(cascade="all, delete-orphan")
    allergies: Mapped[list[Allergy]] = relationship(cascade="all, delete-orphan")
    lifestyle: Mapped[list[LifestyleAssessment]] = relationship(cascade="all, delete-orphan",
                                                                order_by="LifestyleAssessment.recorded_at")


class AccessGrant(Base):
    """A clinician may see a patient's record only while an un-revoked grant exists."""

    __tablename__ = "access_grants"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    clinician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clinician: Mapped[User] = relationship(foreign_keys=[clinician_id])


class Encounter(TimestampMixin, Base):
    __tablename__ = "encounters"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    clinician_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(_enum(*ENCOUNTER_TYPES, name="encounter_type"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    admission_type: Mapped[str | None] = mapped_column(_enum(*ADMISSION_TYPES, name="admission_type"))
    admission_source: Mapped[str | None] = mapped_column(_enum(*ADMISSION_SOURCES, name="admission_source"))
    discharge_disposition: Mapped[str | None] = mapped_column(_enum(*DISPOSITIONS, name="discharge_disposition"))
    procedure_count: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_date: Mapped[date | None] = mapped_column(Date)

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    clinician: Mapped[User | None] = relationship()
    conditions: Mapped[list[Condition]] = relationship(back_populates="encounter", overlaps="conditions")
    observations: Mapped[list[Observation]] = relationship(back_populates="encounter", overlaps="observations")
    medications: Mapped[list[Medication]] = relationship(back_populates="encounter", overlaps="medications")

    __table_args__ = (Index("ix_encounters_patient_started", "patient_id", "started_at"),)


class Condition(TimestampMixin, Base):
    __tablename__ = "conditions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    icd10_code: Mapped[str] = mapped_column(String(10), index=True)
    description: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(_enum(*CONDITION_STATUS, name="condition_status"), default="active")
    # FHIR Condition.category: "problem" = on the patient's problem list; "encounter" = coded for one visit only.
    category: Mapped[str] = mapped_column(_enum(*CONDITION_CATEGORIES, name="condition_category"), default="problem")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    onset_date: Mapped[date | None] = mapped_column(Date)
    resolved_date: Mapped[date | None] = mapped_column(Date)

    encounter: Mapped[Encounter | None] = relationship(back_populates="conditions", overlaps="conditions")


class Observation(TimestampMixin, Base):
    __tablename__ = "observations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(40))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(_enum(*OBS_SOURCES, name="observation_source"), default="clinician")

    encounter: Mapped[Encounter | None] = relationship(back_populates="observations", overlaps="observations")

    __table_args__ = (Index("ix_observations_patient_code_time", "patient_id", "code", "observed_at"),)


class Medication(TimestampMixin, Base):
    __tablename__ = "medications"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str | None] = mapped_column(String(60))
    frequency: Mapped[str | None] = mapped_column(String(60))
    route: Mapped[str | None] = mapped_column(String(30))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(_enum(*MED_STATUS, name="medication_status"), default="active")
    action: Mapped[str] = mapped_column(_enum(*MED_ACTIONS, name="medication_action"), default="started")

    encounter: Mapped[Encounter | None] = relationship(back_populates="medications", overlaps="medications")


class Allergy(TimestampMixin, Base):
    __tablename__ = "allergies"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(_enum(*SEVERITIES, name="allergy_severity"), default="moderate")


class LifestyleAssessment(Base):
    """Short patient questionnaire — inputs to the chronic-disease models that a chart doesn't hold."""

    __tablename__ = "lifestyle_assessments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    smoker: Mapped[bool | None] = mapped_column(Boolean)
    phys_activity: Mapped[bool | None] = mapped_column(Boolean)
    fruits_daily: Mapped[bool | None] = mapped_column(Boolean)
    veggies_daily: Mapped[bool | None] = mapped_column(Boolean)
    heavy_alcohol: Mapped[bool | None] = mapped_column(Boolean)
    general_health: Mapped[int | None] = mapped_column(Integer)  # 1 excellent .. 5 poor
    poor_mental_health_days: Mapped[int | None] = mapped_column(Integer)
    poor_physical_health_days: Mapped[int | None] = mapped_column(Integer)
    difficulty_walking: Mapped[bool | None] = mapped_column(Boolean)


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    clinician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(_enum(*APPT_STATUS, name="appointment_status"), default="scheduled")
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clinician: Mapped[User] = relationship()


class RiskScore(Base):
    __tablename__ = "risk_scores"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    model: Mapped[str] = mapped_column(String(40))
    model_version: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(10))
    percentile: Mapped[int] = mapped_column(Integer)
    factors: Mapped[list] = mapped_column(JSON, default=list)
    missing_features: Mapped[list] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_risk_patient_model_time", "patient_id", "model", "computed_at"),)


class Alert(Base):
    """Acute-risk alert raised when new readings cross clinical thresholds (see services/alerts.py).

    Patients see an alert only after a clinician has reviewed it and released it to them.
    """

    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    level: Mapped[str] = mapped_column(_enum("watch", "urgent", "critical", name="alert_level"))
    news2: Mapped[int | None] = mapped_column(Integer)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(16))  # clinician | patient
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    released_to_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])


class AuditLog(Base):
    """Append-only record of who viewed or changed which patient's data."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(32))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)

    actor: Mapped[User | None] = relationship()
