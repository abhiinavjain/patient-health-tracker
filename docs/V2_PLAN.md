# Patient Health Tracker — v2 Plan

## 1. What v2 is

A centralised, longitudinal health record. A patient's full history (visits, diagnoses, labs, vitals, medications, allergies) lives in one place and is updated after every consultation. An ML layer turns that history into **explainable risk predictions** and **population analytics**.

Two kinds of user:

| Role | Can do |
|---|---|
| **Patient** | See their own timeline, trends (BP, HbA1c, BMI…), and risk scores with plain-language explanations; grant or revoke a clinician's access; book appointments |
| **Clinician / hospital staff** | Search patients they have access to; record a consultation (structured form **or** a free-text note that the NLP extracts); see risk scores with SHAP drivers; see a worklist of high-risk patients |
| **Admin** (hospital) | Manage staff accounts; population analytics dashboard; model monitoring |

> **Scope disclaimer:** this is a portfolio/demo system that runs on synthetic and public de-identified data only. It is not a medical device and is not HIPAA/DPDP-certified. That is stated in the UI and the README.

## 2. What was wrong with v1 (and why this is a rewrite)

- No ML model existed. The frontend posted CT scans to `/api/predict`, which was never implemented.
- The patient record was flat free-text strings, with no notion of a visit, date, doctor, lab value or vital.
- The Express API had no auth, open CORS and no roles. Any client could read or delete every record.
- `sendEmail` was undefined, the reminder cron scanned every appointment every minute, and there were three duplicate backends, a `vercel.json` from an unrelated project, and hardcoded `localhost` URLs.

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui**, TanStack Query, Recharts | Most in-demand React stack; accessible component primitives; good charts for trends |
| API | **FastAPI (Python)** + Pydantic v2 + SQLAlchemy 2 + Alembic | Same language as the ML code, so the model loads in-process with no Node↔Python bridge; OpenAPI docs for free |
| DB | **PostgreSQL** | Medical records are relational (patient → encounters → observations); strong constraints; JSONB where useful |
| Auth | JWT (access + refresh) with role-based access + per-patient consent grants | Real RBAC rather than "logged in = can see everything" |
| ML | pandas, scikit-learn, **LightGBM**, **SHAP**, Optuna, MLflow (optional) | Industry-standard tabular stack |
| NLP | Local, offline extractor (rules + text normalisation + spelling correction, optional trained action classifier) | No patient text leaves the server; deterministic; free to run |
| Jobs | APScheduler or a simple worker for reminders | Replaces the every-minute cron |
| Infra | Docker Compose (web, api, db), GitHub Actions CI (lint, type-check, tests, model tests) | One-command setup for reviewers |

## 4. Data model (FHIR-inspired, simplified)

```
User(id, email, role[patient|clinician|admin], password_hash)
Patient(id, user_id?, name, dob, sex, blood_group, contact…)
AccessGrant(patient_id, clinician_id, granted_at, revoked_at)   ← patient-controlled consent
Encounter(id, patient_id, clinician_id, type[outpatient|inpatient|emergency],
          admitted_at, discharged_at, reason, note_text, discharge_disposition)
Condition(id, patient_id, encounter_id, icd10_code, description, status, onset_date)
Observation(id, patient_id, encounter_id, code[LOINC-ish: bp_sys, bp_dia, bmi, hba1c, glucose…],
            value, unit, observed_at)
Medication(id, patient_id, encounter_id, name, dose, frequency, start, end, status)
Allergy(id, patient_id, substance, reaction, severity)
Appointment(id, patient_id, clinician_id, starts_at, reason, status)
RiskScore(id, patient_id, model_name, model_version, score, top_factors JSONB, computed_at)
AuditLog(id, actor_id, action, entity, entity_id, at)            ← who viewed/changed what
```

"Update history after a consultation" means creating an **Encounter** and attaching Conditions, Observations and Medications to it. The timeline is then simply these rows ordered by date.

## 5. ML components

### 5.1 30-day readmission risk (inpatient encounters)
- **Data:** UCI *Diabetes 130-US Hospitals 1999–2008*, about 100k real de-identified inpatient encounters.
- **Target:** readmitted within 30 days.
- **Rigour points:**
  - Split by patient (`GroupShuffleSplit` on `patient_nbr`), so the same person is never in both train and test.
  - Exclude encounters that ended in death or hospice.
  - Group ICD-9 codes into clinical categories.
  - **Exclude race as a model input** and instead report subgroup performance by race, sex and age.
- **Models:** logistic-regression baseline vs. LightGBM (Optuna-tuned), Platt calibration.
- **Metrics:** ROC-AUC, PR-AUC, Brier score, calibration curve, and precision/recall when flagging the top 10% / 20% of patients. That last one is the operational framing: "we can call 1 in 10 discharged patients; how many readmissions do we catch?"
- **Honest expectation:** the published AUC on this dataset is about 0.65–0.70. The model card states that rather than over-claiming.

### 5.2 Chronic-disease risk (diabetes, cardiovascular)
- **Data:** CDC BRFSS 2015 *Diabetes Health Indicators* (UCI id 891), 253,680 survey respondents.
- **Two models from one dataset:**
  - Diabetes / prediabetes risk.
  - Heart disease / heart attack risk.
- **Inputs:** only features the app can actually collect, from vitals and conditions plus a short lifestyle questionnaire (BMI, BP, cholesterol, smoking, activity, general health, age, sex…). Income and education are dropped on purpose.
- **Outputs:** the same evaluation, calibration and subgroup report as 5.1.

### 5.3 Explainability
- Per-prediction exact TreeSHAP (LightGBM `pred_contrib`), returned as the top increasing and decreasing factors in plain language (e.g. "3 inpatient stays in the past year ↑ risk").
- Global SHAP summary plots in each model's report.

### 5.4 Clinical-note NLP (phase 3)
- The clinician pastes or dictates a consultation note. A **local, offline** extractor (no external LLM; no patient text leaves the server) turns it into conditions, medications (name/action/dose/frequency), vitals and follow-up.
- The clinician **reviews and confirms** before anything is written to the record (human-in-the-loop).
- **Evaluation:** about 50 hand-labelled synthetic notes, scored by field-level precision, recall and F1. This is reported in the README.

### 5.5 Analytics and monitoring (admin dashboard)
- Cohort views: risk distribution, top conditions, readmission rate over time.
- Model monitoring: score drift (PSI) of live predictions vs. the training distribution, and the model version in use.

### 5.6 Serving contract
- Each model ships as `artifacts/<model>/` containing `model.txt`, `calibrator.joblib`, `metadata.json` (feature list, version, metrics, training-data hash) and `report.md`.
- The API loads them at startup. `healthml.predict.RiskModel` is the single inference entry point used by both the API and the tests.

## 6. Repository layout (after v1 is removed)

```
apps/web/        Next.js frontend
apps/api/        FastAPI service (imports ml package for inference)
ml/              training pipeline: data → features → train → evaluate → explain → artifacts
  src/healthml/
  artifacts/     trained models + reports (small; committed)
  data/raw/      downloaded datasets (git-ignored)
infra/           docker-compose, seed scripts
docs/            this plan, model cards, screenshots
```

## 7. Phases

| # | Deliverable | Done when |
|---|---|---|
| **1 ✅** | **ML pipeline**: readmission + diabetes + CVD models, reports, model cards, unit tests | Done: see `ml/README.md` for results |
| **2 ✅** | API + DB: schema, migrations, auth/RBAC/consent, CRUD for encounters etc., `/risk` endpoints, audit log, seeded synthetic patients | Done: 44 endpoints, 21 tests, Docker Compose verified on Postgres |
| **3 ✅** | Note NLP: extraction service + review UI hook + eval set | Done: local extractor, held-out F1 0.76 → 0.96; no external LLM |
| **4 ✅** | Frontend: patient timeline, trend charts, risk cards with SHAP drivers, clinician worklist, consultation form, admin analytics | Done: Next.js 16 app, httpOnly-cookie auth through the Next.js server, verified in the browser and in Docker |
| 5 | Polish: CI, README with screenshots/GIF, deploy (Vercel for web; Render/Fly/Railway for API + managed Postgres) | Public demo link with a demo login |

v1 was removed at the start of phase 2; its source is archived in `legacy/v1-source.tar.gz`.

## 8. How this reads on a résumé (ML / analytics roles)

- "Built patient-level 30-day readmission model on 100k encounters (LightGBM, patient-grouped splits, calibrated, SHAP); reported operational lift at a fixed outreach capacity and subgroup fairness metrics."
- "Shipped models behind a FastAPI service with versioned artifacts and drift monitoring (PSI)."
- "Built an offline clinical-note extractor (ICD-10 diagnoses, medication changes, vitals) that raised held-out F1 from 0.76 to 0.96. Evaluated with frozen held-out sets and an ablation per component; a trained action classifier ships only if it beats the rules in cross-validation."
