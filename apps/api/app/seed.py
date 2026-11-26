"""Generate a reproducible synthetic population for demos and development.

    python -m app.seed --patients 80 --reset

Every person here is fictional. Histories are generated from simple clinical archetypes (healthy, metabolic,
cardiac, frail/multimorbid, respiratory) so the timelines, trends and risk scores look plausible.
Demo logins are printed at the end; the password comes from SEED_PASSWORD (see .env.example).
"""

from __future__ import annotations

import argparse
import os
import random
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from .catalog import OBSERVATIONS
from .db import Base, SessionLocal, engine
from .models import (
    AccessGrant, Allergy, Appointment, Condition, Encounter, LifestyleAssessment, Medication, Observation, Patient,
    User,
)
from .routers.common import new_mrn
from .security import hash_password
from .services.risk import score_and_store

DEMO_DOMAIN = "demo.pht"
DEFAULT_PASSWORD = "demo-password-123"

FIRST_F = ["Aanya", "Priya", "Meera", "Kavya", "Ananya", "Isha", "Neha", "Pooja", "Riya", "Sneha", "Divya", "Lakshmi",
           "Fatima", "Sara", "Grace", "Simran", "Nandini", "Asha", "Rekha", "Sunita"]
FIRST_M = ["Arjun", "Rahul", "Vikram", "Aditya", "Rohan", "Karan", "Imran", "Sanjay", "Manoj", "Rajesh", "Amit",
           "Suresh", "Arun", "Joseph", "Harpreet", "Nikhil", "Varun", "Deepak", "Ravi", "Kabir"]
LAST = ["Sharma", "Verma", "Iyer", "Nair", "Reddy", "Gupta", "Khan", "Singh", "Patel", "Das", "Menon", "Rao",
        "Chatterjee", "Joshi", "Mehta", "Kulkarni", "Fernandes", "Bose", "Pillai", "Agarwal"]

CLINICIANS = [
    ("Dr. Ritu Malhotra", "Internal Medicine"),
    ("Dr. Sameer Kapoor", "Cardiology"),
    ("Dr. Anjali Deshpande", "Family Medicine"),
    ("Dr. Farhan Siddiqui", "Emergency Medicine"),
    ("Dr. Leena Thomas", "Pulmonology"),
]

DX = {
    "t2dm": ("E11.9", "Type 2 diabetes mellitus"),
    "htn": ("I10", "Essential hypertension"),
    "lipid": ("E78.5", "Hyperlipidaemia"),
    "obesity": ("E66.9", "Obesity"),
    "cad": ("I25.10", "Coronary artery disease"),
    "hf": ("I50.9", "Heart failure"),
    "ckd": ("N18.3", "Chronic kidney disease, stage 3"),
    "copd": ("J44.9", "Chronic obstructive pulmonary disease"),
    "asthma": ("J45.909", "Asthma"),
    "gerd": ("K21.9", "Gastro-oesophageal reflux disease"),
    "oa": ("M17.1", "Osteoarthritis of knee"),
    "depression": ("F32.9", "Depressive episode"),
    "prediabetes": ("R73.03", "Prediabetes"),
}
DX_MEDS = {
    "t2dm": [("Metformin", "500 mg", "twice daily")],
    "htn": [("Telmisartan", "40 mg", "once daily"), ("Amlodipine", "5 mg", "once daily")],
    "lipid": [("Atorvastatin", "20 mg", "at night")],
    "cad": [("Aspirin", "75 mg", "once daily"), ("Metoprolol", "25 mg", "twice daily")],
    "hf": [("Furosemide", "40 mg", "once daily")],
    "copd": [("Tiotropium inhaler", "18 mcg", "once daily")],
    "asthma": [("Salbutamol inhaler", "100 mcg", "as needed")],
    "gerd": [("Pantoprazole", "40 mg", "before breakfast")],
    "depression": [("Sertraline", "50 mg", "once daily")],
}
ADMISSIONS = {
    "hf": ("I50.9", "Acute decompensated heart failure", "Breathlessness and leg swelling"),
    "copd": ("J44.1", "COPD with acute exacerbation", "Worsening cough and breathlessness"),
    "t2dm": ("E11.65", "Type 2 diabetes with hyperglycaemia", "High sugars, vomiting"),
    "cad": ("I21.4", "Non-ST elevation myocardial infarction", "Chest pain"),
    "any": ("J18.9", "Pneumonia", "Fever and cough"),
    "ckd": ("N17.9", "Acute kidney injury", "Reduced urine output"),
}

ARCHETYPES = {
    #               weight, conditions pool (prob), admissions/yr, age range
    "healthy":      (0.25, {"gerd": 0.2, "asthma": 0.1, "prediabetes": 0.15, "depression": 0.1}, 0.0, (22, 55)),
    "metabolic":    (0.30, {"t2dm": 0.7, "htn": 0.7, "lipid": 0.6, "obesity": 0.5, "prediabetes": 0.2}, 0.15, (38, 70)),
    "cardiac":      (0.18, {"htn": 0.9, "lipid": 0.8, "cad": 0.8, "t2dm": 0.4, "hf": 0.3}, 0.5, (50, 82)),
    "frail":        (0.15, {"htn": 0.9, "t2dm": 0.6, "hf": 0.6, "ckd": 0.6, "oa": 0.5, "depression": 0.3}, 1.6, (68, 90)),
    "respiratory":  (0.12, {"copd": 0.8, "htn": 0.4, "gerd": 0.3}, 0.8, (50, 80)),
}


IST = timezone(timedelta(hours=5, minutes=30))  # the demo clinic runs on Indian time


def _dt(d: date, hour: int = 10) -> datetime:
    return datetime.combine(d, time(hour, random.choice([0, 15, 30, 45])), tzinfo=IST)


class Gen:
    def __init__(self, db: Session, clinicians: list[User], today: date):
        self.db, self.clinicians, self.today = db, clinicians, today
        self.by_spec = {c.specialty: c for c in clinicians}

    def clinician_for(self, arche: str, kind: str) -> User:
        if kind == "emergency":
            return self.by_spec["Emergency Medicine"]
        if arche == "cardiac":
            return self.by_spec["Cardiology"]
        if arche == "respiratory":
            return self.by_spec["Pulmonology"]
        return self.by_spec["Internal Medicine"] if arche in ("frail", "metabolic") else self.by_spec["Family Medicine"]

    def patient(self, user: User | None = None, sex: str | None = None) -> Patient:
        arche = random.choices(list(ARCHETYPES), weights=[a[0] for a in ARCHETYPES.values()])[0]
        _, pool, adm_rate, (lo, hi) = ARCHETYPES[arche]
        sex = sex or random.choice(["female", "male"])
        first = random.choice(FIRST_F if sex == "female" else FIRST_M)
        name = user.full_name if user else f"{first} {random.choice(LAST)}"
        age = random.randint(lo, hi)
        dob = self.today - timedelta(days=age * 365 + random.randint(0, 364))
        p = Patient(mrn=new_mrn(self.db), full_name=name, date_of_birth=dob, sex=sex, user_id=user.id if user else None,
                    blood_group=random.choice(["A+", "B+", "O+", "AB+", "O-", "A-", "B-"]),
                    phone=f"+91 9{random.randint(100000000, 999999999)}", address=random.choice(
                        ["New Delhi", "Gurugram", "Noida", "Bengaluru", "Pune", "Mumbai", "Chennai", "Hyderabad"]))
        self.db.add(p)
        self.db.flush()

        conds = [k for k, prob in pool.items() if random.random() < prob]
        if "t2dm" in conds and "prediabetes" in conds:
            conds.remove("prediabetes")
        self.history(p, arche, conds, adm_rate)
        return p

    # ------------------------------------------------------------------ history
    def history(self, p: Patient, arche: str, conds: list[str], adm_rate: float) -> None:
        years = random.uniform(1.5, 4)
        start = self.today - timedelta(days=int(years * 365))
        base_w = random.uniform(55, 75) if p.sex == "female" else random.uniform(65, 90)
        if "obesity" in conds or arche == "metabolic":
            base_w *= random.uniform(1.15, 1.35)
        height = random.uniform(150, 168) if p.sex == "female" else random.uniform(162, 182)
        sbp0 = random.uniform(142, 165) if "htn" in conds else random.uniform(108, 132)
        a1c0 = random.uniform(7.4, 9.6) if "t2dm" in conds else random.uniform(5.8, 6.3) if "prediabetes" in conds else random.uniform(4.8, 5.6)
        ldl0 = random.uniform(135, 185) if "lipid" in conds else random.uniform(80, 125)

        # Diagnoses are spread over the first part of the history.
        dx_dates = {c: start + timedelta(days=random.randint(0, max(1, int(years * 365 * 0.5)))) for c in conds}
        treated: set[str] = set()
        grant_to: set = set()

        # Outpatient follow-ups every 2-5 months.
        d = start
        visits = []
        while d < self.today - timedelta(days=7):
            visits.append(d)
            d += timedelta(days=random.randint(60, 150))
        # Inpatient admissions (Poisson-ish), with occasional 30-day readmissions.
        admissions = []
        n_adm = sum(random.random() < adm_rate / 2 for _ in range(int(years * 2)))
        for _ in range(n_adm):
            admissions.append(start + timedelta(days=random.randint(30, int(years * 365) - 5)))
        if adm_rate >= 0.5 and random.random() < 0.55:  # a recent discharge so readmission risk is live
            admissions.append(self.today - timedelta(days=random.randint(4, 24)))
        if admissions and random.random() < 0.3:
            first = min(admissions)
            admissions.append(first + timedelta(days=random.randint(8, 27)))
        emergencies = [start + timedelta(days=random.randint(10, int(years * 365) - 3))
                       for _ in range(sum(random.random() < 0.15 for _ in range(int(years * 2))))]

        events = [(v, "outpatient") for v in visits] + [(a, "inpatient") for a in admissions] + [(e, "emergency") for e in emergencies]
        events.sort()
        last_inpatient_end: date | None = None
        for when, kind in events:
            if kind == "inpatient" and last_inpatient_end and when <= last_inpatient_end:
                continue
            frac = (when - start).days / max(1, (self.today - start).days)
            clin = self.clinician_for(arche, kind)
            grant_to.add(clin.id)
            new_dx = [c for c in conds if dx_dates[c] <= when and c not in treated]

            if kind == "outpatient":
                enc = Encounter(patient_id=p.id, clinician_id=clin.id, type="outpatient", started_at=_dt(when),
                                ended_at=_dt(when) + timedelta(minutes=20),
                                reason=random.choice(["Routine follow-up", "Medication review", "Annual check-up",
                                                      "Review of test results"]) if not new_dx else "New symptoms",
                                follow_up_date=when + timedelta(days=90))
            else:
                key = random.choice([c for c in conds if c in ADMISSIONS] or ["any"])
                code, desc, reason = ADMISSIONS[key]
                los = random.randint(2, 9) if kind == "inpatient" else 0
                end = when + timedelta(days=los)
                if kind == "inpatient" and end >= self.today:
                    end = self.today - timedelta(days=1)
                    los = (end - when).days
                    if los < 1:
                        continue
                disposition = random.choices(["home", "home_health", "facility", "left_ama"], [0.62, 0.2, 0.15, 0.03])[0]
                enc = Encounter(
                    patient_id=p.id, clinician_id=clin.id if kind == "emergency" else self.by_spec["Internal Medicine"].id,
                    type=kind, started_at=_dt(when, 3 if kind == "emergency" else 11),
                    ended_at=_dt(end, 15) if kind == "inpatient" else _dt(when, 7), reason=reason,
                    admission_type="emergency" if kind == "emergency" or random.random() < 0.7 else "urgent",
                    admission_source="emergency_room" if random.random() < 0.7 else "referral",
                    discharge_disposition=disposition if kind == "inpatient" else "home",
                    procedure_count=random.randint(0, 3) if kind == "inpatient" else 0,
                    follow_up_date=end + timedelta(days=7),
                )
                if kind == "inpatient":
                    last_inpatient_end = end
                    grant_to.add(enc.clinician_id)
            self.db.add(enc)
            self.db.flush()

            if kind != "outpatient":
                # Admission diagnosis is coded to the stay; chronic problems live on the problem list.
                self.db.add(Condition(patient_id=p.id, encounter_id=enc.id, icd10_code=code, description=desc,
                                      is_primary=True, onset_date=when, category="encounter",
                                      created_at=_dt(when)))
                for c in [c for c in conds if dx_dates[c] <= when][:4]:
                    if DX[c][0] != code:  # comorbidity coded for this stay (not a new problem-list entry)
                        self.db.add(Condition(patient_id=p.id, encounter_id=enc.id, icd10_code=DX[c][0],
                                              description=DX[c][1], created_at=_dt(when), onset_date=dx_dates[c],
                                              category="encounter"))
            for i, c in enumerate(new_dx):
                self.db.add(Condition(patient_id=p.id, encounter_id=enc.id, icd10_code=DX[c][0], description=DX[c][1],
                                      is_primary=(i == 0 and kind == "outpatient"), onset_date=when,
                                      created_at=_dt(when)))
                for name, dose, freq in DX_MEDS.get(c, []):
                    self.db.add(Medication(patient_id=p.id, encounter_id=enc.id, name=name, dose=dose, frequency=freq,
                                           route="oral" if "inhaler" not in name else "inhaled", start_date=when,
                                           action="started", created_at=_dt(when)))
                treated.add(c)
            # Insulin intensification for poorly controlled diabetes during an admission.
            if kind == "inpatient" and "t2dm" in treated and random.random() < 0.4 and not any(
                    m.name.startswith("Insulin") for m in p.medications):
                self.db.add(Medication(patient_id=p.id, encounter_id=enc.id, name="Insulin glargine", dose="10 units",
                                       frequency="at night", route="subcutaneous", start_date=when, action="started",
                                       created_at=_dt(when)))

            # Vitals at every encounter; treatment brings BP/HbA1c/LDL down over time.
            t_bp = 0.12 if "htn" in treated else 0
            t_a1c = 0.15 if "t2dm" in treated else 0
            t_ldl = 0.3 if "lipid" in treated else 0
            weight = base_w * (1 + random.gauss(0, 0.015) - 0.03 * frac * ("obesity" in treated))
            sbp = sbp0 * (1 - t_bp * min(1, frac * 2)) + random.gauss(0, 6) + (12 if kind != "outpatient" else 0)
            obs = {
                "bp_systolic": round(sbp), "bp_diastolic": round(sbp * random.uniform(0.58, 0.66)),
                "heart_rate": round(random.gauss(92 if kind != "outpatient" else 76, 8)),
                "weight": round(weight, 1), "bmi": round(weight / (height / 100) ** 2, 1),
            }
            if kind != "outpatient":
                obs |= {"temperature": round(random.gauss(37.6, 0.6), 1), "spo2": round(random.uniform(88, 97))}
            chronic_care = arche in ("metabolic", "cardiac", "frail")
            if kind == "inpatient" or random.random() < (0.35 if chronic_care else 0.08) or (chronic_care and when == visits[0]):
                if chronic_care or kind == "inpatient":  # healthy adults mostly get lipids, not HbA1c
                    obs |= {
                        "hba1c": round(max(4.6, a1c0 * (1 - t_a1c * min(1, frac * 2)) + random.gauss(0, 0.3)), 1),
                        "glucose_fasting": round(random.gauss(150 if "t2dm" in conds else 95, 18)),
                    }
                obs |= {
                    "cholesterol_total": round(ldl0 * (1 - t_ldl * min(1, frac * 2)) + 70 + random.gauss(0, 10)),
                    "ldl": round(ldl0 * (1 - t_ldl * min(1, frac * 2)) + random.gauss(0, 8)),
                    "hdl": round(random.gauss(44 if p.sex == "male" else 52, 6)),
                    "creatinine": round(random.gauss(1.7 if "ckd" in conds else 0.9, 0.15), 2),
                }
            if kind == "inpatient":
                obs |= {"hemoglobin": round(random.gauss(11.5, 1.2), 1), "egfr": round(random.gauss(45 if "ckd" in conds else 85, 8)),
                        "glucose_random": round(random.gauss(240 if "t2dm" in conds else 120, 50))}
            for code, value in obs.items():
                self.db.add(Observation(patient_id=p.id, encounter_id=enc.id, code=code, value=float(value),
                                        unit=OBSERVATIONS[code][1], observed_at=enc.started_at, source="clinician"))
            if kind == "outpatient" and when == visits[0]:
                self.db.add(Observation(patient_id=p.id, encounter_id=enc.id, code="height", value=round(height),
                                        unit="cm", observed_at=enc.started_at))

        # Patient-reported data
        if random.random() < 0.8:
            smoker = random.random() < (0.55 if arche == "respiratory" else 0.2)
            unwell = arche in ("frail", "cardiac", "respiratory")
            self.db.add(LifestyleAssessment(
                patient_id=p.id, recorded_at=_dt(self.today - timedelta(days=random.randint(5, 200))),
                smoker=smoker, phys_activity=random.random() < (0.4 if unwell else 0.75),
                fruits_daily=random.random() < 0.6, veggies_daily=random.random() < 0.8,
                heavy_alcohol=random.random() < 0.06,
                general_health=min(5, max(1, round(random.gauss(3.6 if unwell else 2.3, 0.8)))),
                poor_mental_health_days=random.choice([0, 0, 0, 2, 5, 10]),
                poor_physical_health_days=random.choice([0, 0, 3, 7, 15] if unwell else [0, 0, 0, 2]),
                difficulty_walking=random.random() < (0.5 if arche == "frail" else 0.08),
            ))
        if random.random() < 0.25:
            sub, rx, sev = random.choice([("Penicillin", "Rash", "moderate"), ("Sulfonamides", "Hives", "mild"),
                                          ("Peanuts", "Anaphylaxis", "severe"), ("Ibuprofen", "Wheeze", "moderate")])
            self.db.add(Allergy(patient_id=p.id, substance=sub, reaction=rx, severity=sev))
        for cid in grant_to:
            self.db.add(AccessGrant(patient_id=p.id, clinician_id=cid, granted_by=p.user_id,
                                    granted_at=_dt(start)))
        if random.random() < 0.6:
            cid = random.choice(list(grant_to))
            self.db.add(Appointment(patient_id=p.id, clinician_id=cid,
                                    starts_at=_dt(self.today + timedelta(days=random.randint(1, 40)), random.randint(9, 16)),
                                    reason="Follow-up"))


def run(n_patients: int, reset: bool, seed: int = 7, if_empty: bool = False) -> None:
    if if_empty and not reset:
        from sqlalchemy import inspect, select

        if inspect(engine).has_table("users"):
            with SessionLocal() as db:
                if db.scalar(select(User.id).limit(1)) is not None:
                    print("Database already has users; skipping seed.")
                    return
    random.seed(seed)
    password = os.environ.get("SEED_PASSWORD", DEFAULT_PASSWORD)
    pw_hash = hash_password(password)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        admin = User(email=f"admin@{DEMO_DOMAIN}", full_name="Hospital Admin", role="admin", password_hash=pw_hash)
        db.add(admin)
        clinicians = []
        for i, (name, spec) in enumerate(CLINICIANS, 1):
            u = User(email=f"doctor{i}@{DEMO_DOMAIN}", full_name=name, role="clinician", specialty=spec,
                     password_hash=pw_hash)
            db.add(u)
            clinicians.append(u)
        db.flush()
        gen = Gen(db, clinicians, date.today())
        patients = []
        for i in range(n_patients):
            user, sex = None, None
            if i < 3:  # first three patients get logins; the name must match the record's sex
                sex = random.choice(["female", "male"])
                first = random.choice(FIRST_F if sex == "female" else FIRST_M)
                user = User(email=f"patient{i + 1}@{DEMO_DOMAIN}", full_name=f"{first} {random.choice(LAST)}",
                            role="patient", password_hash=pw_hash)
                db.add(user)
                db.flush()
            patients.append(gen.patient(user, sex))
        db.flush()
        for p in patients:
            db.refresh(p)
            score_and_store(db, p)
        db.commit()
        print(f"Seeded {n_patients} patients, {len(clinicians)} clinicians, 1 admin.")
        print(f"Demo logins (password from SEED_PASSWORD, default '{DEFAULT_PASSWORD}'):")
        print(f"  admin@{DEMO_DOMAIN}")
        for i, (name, spec) in enumerate(CLINICIANS, 1):
            print(f"  doctor{i}@{DEMO_DOMAIN}  ({name}, {spec})")
        for i in range(min(3, n_patients)):
            print(f"  patient{i + 1}@{DEMO_DOMAIN}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--patients", type=int, default=80)
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first (destroys data)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--if-empty", action="store_true", help="Only seed when there are no users yet (safe on every boot)")
    args = parser.parse_args()
    run(args.patients, args.reset, args.seed, args.if_empty)


if __name__ == "__main__":
    main()
