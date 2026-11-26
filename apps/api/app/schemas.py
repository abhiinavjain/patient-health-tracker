from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .catalog import OBSERVATIONS, PLAUSIBLE

Role = Literal["patient", "clinician", "admin"]
Sex = Literal["female", "male", "other"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------- auth & users
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class PatientSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: date
    sex: Sex
    phone: str | None = None


class StaffCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    role: Literal["clinician", "admin"]
    specialty: str | None = None


class UserOut(ORM):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    specialty: str | None
    is_active: bool
    patient_id: uuid.UUID | None = None


class ClinicianOut(ORM):
    id: uuid.UUID
    full_name: str
    specialty: str | None


# ----------------------------------------------------------------------------- patients
class PatientBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: date
    sex: Sex
    blood_group: str | None = Field(default=None, pattern=r"^(A|B|AB|O)[+-]$")
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    blood_group: str | None = Field(default=None, pattern=r"^(A|B|AB|O)[+-]$")
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None


class PatientOut(ORM, PatientBase):
    id: uuid.UUID
    mrn: str
    created_at: datetime
    age: int | None = None


class PatientListItem(ORM):
    id: uuid.UUID
    mrn: str
    full_name: str
    date_of_birth: date
    sex: Sex
    age: int | None = None
    last_encounter_at: datetime | None = None
    latest_risk: dict[str, str] = {}  # model -> band


# ----------------------------------------------------------------------------- clinical records
class ConditionIn(BaseModel):
    icd10_code: str = Field(pattern=r"^[A-Za-z][0-9][0-9A-Za-z](\.?[0-9A-Za-z]{1,4})?$")
    description: str = Field(min_length=2, max_length=300)
    status: Literal["active", "resolved"] = "active"
    # "problem" adds it to the ongoing problem list; "encounter" codes it for this visit only.
    category: Literal["problem", "encounter"] = "problem"
    is_primary: bool = False
    onset_date: date | None = None

    @field_validator("icd10_code")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class ConditionOut(ORM, ConditionIn):
    id: uuid.UUID
    encounter_id: uuid.UUID | None
    resolved_date: date | None
    created_at: datetime


class ConditionUpdate(BaseModel):
    status: Literal["active", "resolved"]
    resolved_date: date | None = None


class ObservationIn(BaseModel):
    code: str
    value: float
    unit: str | None = None
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def known_code(self) -> ObservationIn:
        if self.code not in OBSERVATIONS:
            raise ValueError(f"Unknown observation code {self.code!r}")
        expected = OBSERVATIONS[self.code][1]
        if self.unit is None:
            self.unit = expected
        elif self.unit != expected:
            raise ValueError(f"{self.code} must be recorded in {expected}")
        lo, hi = PLAUSIBLE.get(self.code, (float("-inf"), float("inf")))
        if not lo <= self.value <= hi:
            raise ValueError(f"{OBSERVATIONS[self.code][0]} of {self.value:g} {expected} is outside the plausible range "
                             f"({lo:g}–{hi:g}); please check the value")
        return self


class ObservationOut(ORM):
    id: uuid.UUID
    encounter_id: uuid.UUID | None
    code: str
    value: float
    unit: str
    observed_at: datetime
    source: str


class MedicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    start_date: date | None = None
    action: Literal["started", "continued", "dose_increased", "dose_decreased", "stopped"] = "started"


class MedicationOut(ORM):
    id: uuid.UUID
    encounter_id: uuid.UUID | None
    name: str
    dose: str | None
    frequency: str | None
    route: str | None
    start_date: date | None
    end_date: date | None
    status: str
    action: str


class AllergyIn(BaseModel):
    substance: str = Field(min_length=2, max_length=120)
    reaction: str | None = None
    severity: Literal["mild", "moderate", "severe"] = "moderate"


class AllergyOut(ORM, AllergyIn):
    id: uuid.UUID
    created_at: datetime


class LifestyleIn(BaseModel):
    smoker: bool | None = None
    phys_activity: bool | None = None
    fruits_daily: bool | None = None
    veggies_daily: bool | None = None
    heavy_alcohol: bool | None = None
    general_health: int | None = Field(default=None, ge=1, le=5)
    poor_mental_health_days: int | None = Field(default=None, ge=0, le=30)
    poor_physical_health_days: int | None = Field(default=None, ge=0, le=30)
    difficulty_walking: bool | None = None


class LifestyleOut(ORM, LifestyleIn):
    id: uuid.UUID
    recorded_at: datetime


# ----------------------------------------------------------------------------- encounters (consultations)
class EncounterIn(BaseModel):
    """One consultation or admission, with everything recorded during it, saved atomically."""

    type: Literal["outpatient", "inpatient", "emergency", "telehealth"]
    started_at: datetime
    ended_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=300)
    notes: str | None = None
    admission_type: Literal["emergency", "urgent", "elective"] | None = None
    admission_source: Literal["emergency_room", "referral", "transfer", "other"] | None = None
    discharge_disposition: Literal["home", "home_health", "facility", "left_ama", "expired", "other"] | None = None
    procedure_count: int = Field(default=0, ge=0)
    follow_up_date: date | None = None
    conditions: list[ConditionIn] = []
    observations: list[ObservationIn] = []
    medications: list[MedicationIn] = []
    # IDs of existing active medications to stop at this visit.
    stop_medication_ids: list[uuid.UUID] = []

    @model_validator(mode="after")
    def check(self) -> EncounterIn:
        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError("ended_at must be after started_at")
        if sum(c.is_primary for c in self.conditions) > 1:
            raise ValueError("At most one primary diagnosis per encounter")
        return self


class EncounterOut(ORM):
    id: uuid.UUID
    type: str
    started_at: datetime
    ended_at: datetime | None
    reason: str | None
    notes: str | None
    admission_type: str | None
    admission_source: str | None
    discharge_disposition: str | None
    procedure_count: int
    follow_up_date: date | None
    clinician: ClinicianOut | None
    conditions: list[ConditionOut]
    observations: list[ObservationOut]
    medications: list[MedicationOut]


class EncounterSummary(ORM):
    id: uuid.UUID
    type: str
    started_at: datetime
    ended_at: datetime | None
    reason: str | None
    clinician: ClinicianOut | None
    diagnoses: list[str] = []


# ----------------------------------------------------------------------------- summary / timeline
class LatestObservation(BaseModel):
    code: str
    label: str
    value: float
    unit: str
    observed_at: datetime


class PatientSummary(BaseModel):
    patient: PatientOut
    active_conditions: list[ConditionOut]
    active_medications: list[MedicationOut]
    allergies: list[AllergyOut]
    latest_observations: list[LatestObservation]
    last_encounter: EncounterSummary | None
    upcoming_appointments: list[AppointmentOut]
    encounter_count: int


class TimelineEvent(BaseModel):
    at: datetime
    kind: Literal["encounter", "condition", "medication", "observation", "allergy", "risk"]
    title: str
    detail: str | None = None
    encounter_id: uuid.UUID | None = None
    ref_id: uuid.UUID | None = None


class ObservationPoint(BaseModel):
    observed_at: datetime
    value: float
    source: str


class ObservationSeries(BaseModel):
    code: str
    label: str
    unit: str
    points: list[ObservationPoint]


# ----------------------------------------------------------------------------- access, appointments, audit
class GrantIn(BaseModel):
    clinician_id: uuid.UUID


class GrantOut(ORM):
    id: uuid.UUID
    clinician: ClinicianOut
    granted_at: datetime
    revoked_at: datetime | None


class AppointmentIn(BaseModel):
    clinician_id: uuid.UUID
    starts_at: datetime
    reason: str | None = Field(default=None, max_length=300)


class AppointmentUpdate(BaseModel):
    status: Literal["scheduled", "completed", "cancelled", "no_show"] | None = None
    starts_at: datetime | None = None


class AppointmentOut(ORM):
    id: uuid.UUID
    patient_id: uuid.UUID
    clinician: ClinicianOut
    starts_at: datetime
    reason: str | None
    status: str


class AuditOut(ORM):
    at: datetime
    actor_name: str | None = None
    actor_role: str | None
    action: str
    patient_id: uuid.UUID | None
    entity: str | None
    entity_id: str | None


# ----------------------------------------------------------------------------- risk
class RiskFactor(BaseModel):
    feature: str
    label: str
    display_value: str
    direction: Literal["increases", "decreases"]
    impact: float


class RiskResult(BaseModel):
    model: str
    title: str
    status: Literal["scored", "not_applicable", "insufficient_data"]
    reason: str | None = None
    model_version: str | None = None
    score: float | None = None
    band: Literal["low", "moderate", "high"] | None = None
    percentile: int | None = None
    completeness: float | None = None
    factors: list[RiskFactor] = []
    missing_inputs: list[str] = []
    computed_at: datetime | None = None
    encounter_id: uuid.UUID | None = None


class RiskHistoryPoint(BaseModel):
    computed_at: datetime
    score: float
    band: str
    model_version: str


PatientSummary.model_rebuild()
