"""Patient record -> model inputs.

Each builder returns (features, applicability). The mapping choices mirror how the training datasets
define each variable; where the app's data is necessarily different (e.g. the training data counts every lab
test billed during an admission), the model card's limitations apply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from healthml.tasks.readmission import icd10_group

from ..catalog import DIABETES_DRUGS, LAB_CODES, SPECIALTY_MAP, icd_prefix_in
from ..models import Condition, Encounter, Medication, Observation, Patient

READMISSION_WINDOW_DAYS = 30
# Re-screen for diabetes every 3 years after a normal result (ADA / USPSTF practice).
SCREENING_INTERVAL_DAYS = 3 * 365

HYPERTENSION = ("I10", "I11", "I12", "I13", "I15", "I16")
HYPERLIPIDEMIA = ("E78",)
DIABETES_DX = ("E08", "E09", "E10", "E11", "E13", "R73.0")
CHD = ("I20", "I21", "I22", "I23", "I24", "I25")
STROKE = ("I60", "I61", "I62", "I63", "I64", "I69", "Z86.73")
TOBACCO = ("F17", "Z72.0", "Z87.891")


@dataclass
class Built:
    features: dict
    status: str = "scored"  # scored | not_applicable
    reason: str | None = None
    encounter_id: object = None
    notes: list[str] = field(default_factory=list)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _age(dob: date, at: date) -> float:
    return float(at.year - dob.year - ((at.month, at.day) < (dob.month, dob.day)))


def _sex(patient: Patient) -> str | None:
    return patient.sex if patient.sex in ("female", "male") else None


def _active_conditions(patient: Patient, at: datetime | None = None) -> list[Condition]:
    out = []
    for c in patient.conditions:
        if c.status == "resolved" and (at is None or (c.resolved_date and c.resolved_date <= at.date())):
            continue
        if at is not None and _aware(c.created_at) > at:
            continue
        out.append(c)
    return out


def _has_dx(conditions: list[Condition], prefixes: tuple[str, ...]) -> bool:
    return any(icd_prefix_in(c.icd10_code, *prefixes) for c in conditions)


def _obs(patient: Patient, code: str, since: datetime | None = None, until: datetime | None = None) -> list[Observation]:
    rows = [o for o in patient.observations if o.code == code
            and (since is None or _aware(o.observed_at) >= since) and (until is None or _aware(o.observed_at) <= until)]
    return sorted(rows, key=lambda o: _aware(o.observed_at))


def _latest(patient: Patient, code: str) -> float | None:
    rows = _obs(patient, code)
    return rows[-1].value if rows else None


def _is_diabetes_drug(m: Medication) -> bool:
    name = m.name.lower()
    return any(d in name for d in DIABETES_DRUGS)


# ----------------------------------------------------------------------------- readmission
def latest_discharge(patient: Patient, now: datetime) -> Encounter | None:
    done = [e for e in patient.encounters if e.type == "inpatient" and e.ended_at is not None]
    return max(done, key=lambda e: _aware(e.ended_at)) if done else None


def readmission_features(patient: Patient, now: datetime | None = None) -> Built:
    now = now or datetime.now(timezone.utc)
    enc = latest_discharge(patient, now)
    if enc is None:
        return Built({}, "not_applicable", "No inpatient admission on record.")
    discharged = _aware(enc.ended_at)
    if enc.discharge_disposition == "expired":
        return Built({}, "not_applicable", "Encounter ended in death.", enc.id)
    if now - discharged > timedelta(days=READMISSION_WINDOW_DAYS):
        return Built({}, "not_applicable",
                     f"Last discharge was {(now - discharged).days} days ago (score applies to the 30 days after discharge).",
                     enc.id)

    start = _aware(enc.started_at)
    year_before = start - timedelta(days=365)
    prior = [e for e in patient.encounters if e.id != enc.id and _aware(e.started_at) < start]
    prior_year = [e for e in prior if _aware(e.started_at) >= year_before]

    window_obs = [o for o in patient.observations
                  if o.encounter_id == enc.id or start <= _aware(o.observed_at) <= discharged]
    labs = [o for o in window_obs if o.code in LAB_CODES]
    a1c = [o.value for o in window_obs if o.code == "hba1c"]
    glucose = [o.value for o in window_obs if o.code in ("glucose_fasting", "glucose_random", "glucose_postprandial")]

    active_meds = [m for m in patient.medications
                   if m.encounter_id == enc.id or (m.status == "active" and (m.start_date is None or m.start_date <= discharged.date()))]
    enc_meds = [m for m in patient.medications if m.encounter_id == enc.id]
    dm_meds = {m.name.lower() for m in active_meds if _is_diabetes_drug(m) and m.action != "stopped"}
    dm_changes = [m for m in enc_meds if _is_diabetes_drug(m) and m.action in ("dose_increased", "dose_decreased")]
    dm_any_change = [m for m in enc_meds if _is_diabetes_drug(m) and m.action != "continued"]

    insulin = "no"
    insulin_enc = [m for m in enc_meds if "insulin" in m.name.lower()]
    if insulin_enc:
        act = insulin_enc[-1].action
        insulin = {"started": "up", "dose_increased": "up", "dose_decreased": "down", "stopped": "down"}.get(act, "steady")
    elif any("insulin" in m.name.lower() for m in active_meds):
        insulin = "steady"

    enc_dx = sorted([c for c in patient.conditions if c.encounter_id == enc.id], key=lambda c: (not c.is_primary, c.created_at))
    groups = [icd10_group(c.icd10_code) for c in enc_dx[:3]] + ["missing"] * 3
    active_dx = {c.icd10_code for c in _active_conditions(patient, discharged)} | {c.icd10_code for c in enc_dx}

    spec = enc.clinician.specialty.lower() if enc.clinician and enc.clinician.specialty else None
    specialty = SPECIALTY_MAP.get(spec, "other") if spec else "missing"

    def band(values, cuts):
        if not values:
            return "not_measured"
        v = max(values)
        for cut, label in cuts:
            if v > cut:
                return label
        return "Norm"

    features = {
        "age_years": _age(patient.date_of_birth, discharged.date()),
        "sex": _sex(patient),
        "time_in_hospital": float(max(1, (discharged.date() - start.date()).days)),
        "num_lab_procedures": float(len(labs)),
        "num_procedures": float(enc.procedure_count or 0),
        "num_medications": float(len({m.name.lower() for m in active_meds})),
        "number_outpatient": float(sum(e.type in ("outpatient", "telehealth") for e in prior_year)),
        "number_emergency": float(sum(e.type == "emergency" for e in prior_year)),
        "number_inpatient": float(sum(e.type == "inpatient" for e in prior_year)),
        "number_diagnoses": float(len(active_dx)),
        "n_diabetes_meds": float(len(dm_meds)),
        "n_med_changes": float(len(dm_changes)),
        "med_change": float(bool(dm_any_change)),
        "on_diabetes_med": float(bool(dm_meds)),
        "prior_encounters": float(sum(e.type == "inpatient" for e in prior)),
        "admission_type": enc.admission_type,
        "discharge_to": enc.discharge_disposition if enc.discharge_disposition != "expired" else None,
        "admission_source": enc.admission_source,
        "specialty": specialty,
        "diag_1_group": groups[0],
        "diag_2_group": groups[1],
        "diag_3_group": groups[2],
        "a1c_result": band(a1c, [(8, ">8"), (7, ">7")]),
        "max_glucose": band(glucose, [(300, ">300"), (200, ">200")]),
        "insulin": insulin,
    }
    return Built(features, encounter_id=enc.id)


# ----------------------------------------------------------------------------- chronic disease
def _chronic_common(patient: Patient, now: datetime) -> dict:
    active = _active_conditions(patient)
    lifestyle = patient.lifestyle[-1] if patient.lifestyle else None

    bmi = _latest(patient, "bmi")
    if bmi is None:
        w, h = _latest(patient, "weight"), _latest(patient, "height")
        if w and h:
            bmi = round(w / (h / 100) ** 2, 1)

    sys_r = [o.value for o in _obs(patient, "bp_systolic")][-3:]
    dia_r = [o.value for o in _obs(patient, "bp_diastolic")][-3:]
    if _has_dx(active, HYPERTENSION):
        high_bp = 1.0
    elif sys_r or dia_r:
        high_sys = bool(sys_r) and sum(sys_r) / len(sys_r) >= 140
        high_dia = bool(dia_r) and sum(dia_r) / len(dia_r) >= 90
        high_bp = float(high_sys or high_dia)
    else:
        high_bp = None

    five_years = now - timedelta(days=5 * 365)
    lipids = _obs(patient, "cholesterol_total", since=five_years) + _obs(patient, "ldl", since=five_years)
    tc, ldl = _latest(patient, "cholesterol_total"), _latest(patient, "ldl")
    if _has_dx(active, HYPERLIPIDEMIA):
        high_chol = 1.0
    elif tc is not None or ldl is not None:
        high_chol = float((tc or 0) >= 240 or (ldl or 0) >= 160)
    else:
        high_chol = None

    smoker = getattr(lifestyle, "smoker", None)
    if _has_dx(patient.conditions, TOBACCO):
        smoker = True

    def b(v):
        return None if v is None else float(bool(v))

    return {
        "age_years": _age(patient.date_of_birth, now.date()),
        "sex_male": None if _sex(patient) is None else float(patient.sex == "male"),
        "bmi": bmi,
        "high_bp": high_bp,
        "high_chol": high_chol,
        "chol_check_5y": 1.0 if lipids else None,
        "smoker": b(smoker),
        # Problem-list phenotypes: absence from a maintained problem list is treated as "no".
        "stroke": float(_has_dx(patient.conditions, STROKE)),
        "phys_activity": b(getattr(lifestyle, "phys_activity", None)),
        "fruits_daily": b(getattr(lifestyle, "fruits_daily", None)),
        "veggies_daily": b(getattr(lifestyle, "veggies_daily", None)),
        "heavy_alcohol": b(getattr(lifestyle, "heavy_alcohol", None)),
        "general_health": getattr(lifestyle, "general_health", None),
        "poor_mental_health_days": getattr(lifestyle, "poor_mental_health_days", None),
        "poor_physical_health_days": getattr(lifestyle, "poor_physical_health_days", None),
        "difficulty_walking": b(getattr(lifestyle, "difficulty_walking", None)),
    }


def _has_diabetes(patient: Patient) -> bool:
    a1c = _latest(patient, "hba1c")
    return _has_dx(_active_conditions(patient), DIABETES_DX) or (a1c is not None and a1c >= 6.5)


def diabetes_features(patient: Patient, now: datetime | None = None) -> Built:
    now = now or datetime.now(timezone.utc)
    if _has_diabetes(patient):
        return Built({}, "not_applicable", "Diabetes or prediabetes is already recorded — this is a screening model.")
    # The model's job is "who should be offered a test?". A recent HbA1c answers that directly.
    recent = _obs(patient, "hba1c", since=now - timedelta(days=SCREENING_INTERVAL_DAYS))
    if recent:
        last = recent[-1]
        when = _aware(last.observed_at).date().isoformat()
        if last.value >= 5.7:
            return Built({}, "not_applicable",
                         f"HbA1c {last.value:g}% on {when} is in the prediabetes range — manage rather than screen.")
        return Built({}, "not_applicable", f"Screening up to date: HbA1c {last.value:g}% on {when} was normal.")
    f = _chronic_common(patient, now)
    f["heart_disease"] = float(_has_dx(patient.conditions, CHD))
    return Built(f)


def cvd_features(patient: Patient, now: datetime | None = None) -> Built:
    now = now or datetime.now(timezone.utc)
    if _has_dx(patient.conditions, CHD):
        return Built({}, "not_applicable", "Coronary heart disease is already recorded.")
    f = _chronic_common(patient, now)
    f["diabetes"] = float(_has_diabetes(patient))
    return Built(f)


BUILDERS = {
    "readmission_30d": readmission_features,
    "diabetes_risk": diabetes_features,
    "cvd_risk": cvd_features,
}
