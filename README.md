# Patient Health Tracker v2

[![CI](https://github.com/abhiinavjain/patient-health-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/abhiinavjain/patient-health-tracker/actions/workflows/ci.yml)

**Live demo:** _coming soon_ (see [docs/DEPLOY.md](docs/DEPLOY.md)) · one-click demo logins for clinician, patient and admin.

A centralised, longitudinal health record with **explainable ML risk predictions**. Every consultation updates the patient's history as structured data: visits, diagnoses, vitals, labs and medications. Three calibrated models turn that history into risk scores that clinicians can act on.

> Portfolio / demo system. It runs on **synthetic patients** and public de-identified training data. It is not a medical device and is not certified for real patient data.

| | |
|---|---|
| **Patients** | Own timeline and trends; grant and revoke clinician access; see who viewed their record; lifestyle questionnaire; book appointments |
| **Clinicians** | Panel of consented patients; record a consultation in one atomic call; risk scores with SHAP drivers; high-risk worklist |
| **Admins** | Staff accounts, audit log, population analytics, model drift monitoring. They **cannot** open individual charts (least privilege). |

| Clinician worklist | Patient chart |
|---|---|
| ![Risk worklist](docs/screenshots/worklist.jpg) | ![Patient chart](docs/screenshots/patient-chart.jpg) |
| **Explainable risk** | **Sign-in with demo roles** |
| ![Risk cards with SHAP drivers](docs/screenshots/risk.jpg) | ![Sign in](docs/screenshots/sign-in.jpg) |

## Architecture

```
Browser ──▶ Next.js (web)  ── route handlers keep tokens in httpOnly cookies, proxy /api/proxy/* ──▶ FastAPI /api/v1 ──▶ PostgreSQL
                                                                                                     │
                                                                  healthml (in-process): LightGBM + TreeSHAP; local note NLP
```

| Path | What |
|---|---|
| [`apps/web/`](apps/web/README.md) | Next.js 16 frontend: clinician, patient and admin experiences |
| [`ml/`](ml/README.md) | Training pipeline, model cards, inference package (`healthml`) |
| [`apps/api/`](apps/api) | FastAPI service: SQLAlchemy models, Alembic migrations, routers, tests, seed generator |
| [`docs/V2_PLAN.md`](docs/V2_PLAN.md) | Product and architecture plan, phases |
| Tag [`v1.0`](https://github.com/abhiinavjain/patient-health-tracker/tree/v1.0) | The original v1 (React + Express + MongoDB) |

## Models

| Model | Data | Test ROC-AUC (95% CI) | Used when |
|---|---|---|---|
| 30-day readmission | UCI Diabetes 130-US Hospitals (100k encounters) | 0.687 (0.673–0.701) | Inpatient discharged in the last 30 days |
| Diabetes screening | CDC BRFSS 2015 (253k) | 0.827 (0.821–0.832) | No diabetes/prediabetes recorded and no HbA1c in the last 3 years |
| Coronary heart disease | CDC BRFSS 2015 (253k) | 0.851 (0.845–0.857) | No CHD recorded |

The models are calibrated and evaluated with patient-grouped splits and subgroup fairness reports; see the [model cards](ml/README.md#results-held-out-test-set). Each score in the API comes with:
- its band and percentile;
- its top SHAP factors in plain language;
- the inputs that are missing, so the UI can ask for them.

A score is withheld when it isn't clinically meaningful, and the response says why ("not applicable" or "insufficient data").

## Frontend

| Role | What they get |
|---|---|
| **Clinician** | Risk worklist ranked by band and percentile; patient search; the chart (allergy alerts, problems, meds, out-of-range labs, trend charts with normal ranges, risk cards with SHAP drivers, filterable history with visit details); the consultation workspace (free-text note → extracted draft with evidence quotes → edit → save); schedule; panel analytics |
| **Patient** | Their own record in plain language; a 9-question health check that unlocks the chronic-disease estimates; appointment booking; grant and revoke doctor access; "who looked at my record" |
| **Admin** | Population analytics (volume, observed readmissions, risk bands, conditions); model drift (PSI) with test metrics; staff accounts; audit log |

It supports light and dark mode, adapts to phone width, and is keyboard- and screen-reader-friendly (labelled controls, `aria-current` navigation, alerts for severe allergies).

## Clinical-note NLP

`POST /api/v1/patients/{id}/notes/extract` turns a free-text consultation note into a **draft** encounter for the clinician to review and save. The draft contains ICD-10 diagnoses, medications with started/continued/changed/stopped, vitals and labs in canonical units, and the follow-up date.

| | |
|---|---|
| Runs locally | No external LLM or API: no patient text leaves the server. Deterministic, about 5 ms per note |
| How | Rules plus text normalisation (spoken-out numbers, abbreviations, Hinglish, spelling correction) plus an expanded drug/condition lexicon. A trained action classifier ships only if it beats the rules in cross-validation |
| Safety | Evidence quotes from the original note, ICD-10 and plausibility validation, reconciliation against the chart. Nothing is written without clinician approval. Note text is never stored in the audit log |
| Evaluation | 64 labelled synthetic notes. On a **held-out set written before development**, F1 went from 0.76 (v1) to **0.96**, with precision 1.00. See [`apps/api/eval/README.md`](apps/api/eval/README.md) |

## Quick start (Docker)

```bash
docker compose up -d --build                         # Postgres (host 5433) + API (8000) + web (3000)
docker compose run --rm api python -m app.seed       # 80 synthetic patients + demo accounts
```

Open **http://localhost:3000** and pick a demo role on the sign-in page. The API docs are at http://localhost:8000/docs. The password for all of them is `SEED_PASSWORD`, default `demo-password-123`.

| Login | Role |
|---|---|
| `doctor1@demo.pht` … `doctor5@demo.pht` | Clinicians (internal medicine, cardiology, family medicine, emergency, pulmonology) |
| `patient1@demo.pht` … `patient3@demo.pht` | Patients |
| `admin@demo.pht` | Admin |

## Local development

```bash
# ML package (needed by the API for inference)
python3 -m venv ml/.venv && ml/.venv/bin/pip install -e "ml[train,dev]"

# API
cd apps/api
python3 -m venv .venv && .venv/bin/pip install -e ../../ml -e ".[dev]"
.venv/bin/pytest                                     # 36 tests, in-memory SQLite, real model artifacts
docker compose up -d db                              # or point DATABASE_URL at your own Postgres
export DATABASE_URL=postgresql+psycopg://pht:pht@localhost:5433/pht
.venv/bin/alembic upgrade head && .venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

## API overview (`/api/v1`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup` (patients), `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `GET /clinicians` |
| Record | `GET/POST /patients`, `GET/PATCH /patients/{id}`, `/summary`, `/timeline`, `/observations/series?codes=` |
| Consultations | `POST /patients/{id}/encounters`: one call records the visit plus its diagnoses, vitals/labs and medication starts/stops, then re-scores risk |
| Note NLP | `POST /patients/{id}/notes/extract`: free-text note → reviewable draft encounter |
| Problem & med lists | `/conditions`, `/medications` (+ `/stop`), `/allergies`, `/lifestyle`, `/observations` |
| Consent & audit | `GET/POST/DELETE /patients/{id}/access`, `GET /patients/{id}/audit` |
| Appointments | `POST /patients/{id}/appointments`, `GET /appointments`, `PATCH /appointments/{id}` |
| Risk | `GET /patients/{id}/risk`, `POST …/risk/recompute`, `GET …/risk/{model}/history`, `GET /risk/models` |
| Analytics | `GET /analytics/overview`, `GET /analytics/worklist`, `GET /analytics/models` (PSI drift) |
| Admin | `POST/GET/PATCH /admin/users`, `GET /admin/audit` |

## Security and privacy design

- **Access control.** Access is checked per patient on every request: patient = self; clinician = active consent grant; admin = no chart access.
- **Passwords.** Hashed with Argon2id. Login has no user enumeration: an unknown email takes about as long as a wrong password.
- **Tokens.** Short-lived access JWTs plus refresh JWTs, each typed so one can't stand in for the other. Deactivated users lose access immediately.
- **Audit log.** Append-only, recording every chart view and change. Patients can see who accessed their record.
- **Secrets and CORS.** The API refuses to start outside dev without `JWT_SECRET`. CORS is restricted to configured origins.

- Failed sign-ins are throttled per account (5 within 15 minutes), counted for unknown emails too, so a lockout reveals nothing about which accounts exist. The web tier sends standard security headers (frame denial, nosniff, referrer policy, HSTS when served over HTTPS).

Known gaps before any real use:
- Refresh-token revocation.
- Encryption at rest.
- HTTPS termination.
- Formal compliance review (HIPAA / India DPDP).

## Roadmap

- **Phase 3:** ✅ clinical-note NLP, local and offline.
- **Phase 4:** ✅ Next.js frontend.
- **Phase 5:** ✅ CI (ML, API, Postgres migrations, web build, full-stack Docker smoke test) and deployment config for Vercel + Render + Neon ([docs/DEPLOY.md](docs/DEPLOY.md)).

See [docs/V2_PLAN.md](docs/V2_PLAN.md).
