"""Population analytics, clinician worklist and model monitoring.

Admins see the whole population (aggregates only); clinicians see their own panel.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import DB, require_roles
from ..models import AccessGrant, Condition, Encounter, Patient, RiskScore, User
from ..services.risk import available_models, latest_scores
from .common import age_on

router = APIRouter(prefix="/analytics", tags=["analytics"])
Staff = Depends(require_roles("admin", "clinician"))


def _scope(db: Session, user: User) -> list:
    stmt = select(Patient.id)
    if user.role == "clinician":
        stmt = stmt.join(AccessGrant, AccessGrant.patient_id == Patient.id).where(
            AccessGrant.clinician_id == user.id, AccessGrant.revoked_at.is_(None)).distinct()
    return list(db.scalars(stmt).all())


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _months(n: int) -> list[str]:
    d = date.today().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d.strftime("%Y-%m"))
        d = (d - timedelta(days=1)).replace(day=1)
    return list(reversed(out))


@router.get("/overview")
def overview(db: DB, user: User = Staff, months: int = Query(12, ge=1, le=36)):
    ids = _scope(db, user)
    patients = db.scalars(select(Patient).where(Patient.id.in_(ids))).all() if ids else []
    encs = db.scalars(select(Encounter).where(Encounter.patient_id.in_(ids))).all() if ids else []
    labels = _months(months)

    volume = {m: Counter() for m in labels}
    for e in encs:
        key = _aware(e.started_at).strftime("%Y-%m")
        if key in volume:
            volume[key][e.type] += 1

    # Observed 30-day readmissions: inpatient discharge followed by another inpatient admission within 30 days.
    by_patient: dict = {}
    for e in encs:
        if e.type == "inpatient":
            by_patient.setdefault(e.patient_id, []).append(e)
    readmit = {m: [0, 0] for m in labels}
    for stays in by_patient.values():
        stays.sort(key=lambda e: _aware(e.started_at))
        for i, e in enumerate(stays):
            if e.ended_at is None or e.discharge_disposition == "expired":
                continue
            key = _aware(e.ended_at).strftime("%Y-%m")
            if key not in readmit:
                continue
            readmit[key][0] += 1
            nxt = stays[i + 1] if i + 1 < len(stays) else None
            if nxt and _aware(nxt.started_at) - _aware(e.ended_at) <= timedelta(days=30):
                readmit[key][1] += 1

    risks = latest_scores(db, ids)
    bands: dict = {}
    for per_model in risks.values():
        for model, r in per_model.items():
            bands.setdefault(model, Counter())[r.band] += 1

    conditions = db.scalars(select(Condition).where(
        Condition.patient_id.in_(ids), Condition.status == "active", Condition.category == "problem")).all() if ids else []
    seen = set()
    top = Counter()
    for c in conditions:
        if (c.patient_id, c.icd10_code) not in seen:
            seen.add((c.patient_id, c.icd10_code))
            top[(c.icd10_code, c.description)] += 1

    ages = Counter()
    for p in patients:
        a = age_on(p.date_of_birth)
        ages["<30" if a < 30 else "30-44" if a < 45 else "45-64" if a < 65 else "65+"] += 1

    return {
        "scope": "population" if user.role == "admin" else "my_patients",
        "totals": {"patients": len(patients), "encounters": len(encs),
                   "inpatient_stays": sum(e.type == "inpatient" for e in encs)},
        "encounters_by_month": [{"month": m, **{t: volume[m].get(t, 0) for t in
                                                ("outpatient", "inpatient", "emergency", "telehealth")}}
                                for m in labels],
        "readmissions_by_month": [{"month": m, "discharges": d, "readmitted_30d": r,
                                   "rate": (r / d) if d else None} for m, (d, r) in readmit.items()],
        "risk_bands": {m: {b: c.get(b, 0) for b in ("low", "moderate", "high")} for m, c in bands.items()},
        "top_conditions": [{"icd10_code": k[0], "description": k[1], "patients": n} for k, n in top.most_common(10)],
        "age_bands": {k: ages.get(k, 0) for k in ("<30", "30-44", "45-64", "65+")},
        "sex": dict(Counter(p.sex for p in patients)),
    }


@router.get("/worklist")
def worklist(db: DB, user: User = Depends(require_roles("clinician")), model: str | None = None,
             min_band: str = Query("moderate", pattern="^(moderate|high)$")):
    """Patients on my panel whose latest score is moderate/high, highest band/percentile first, with the main driver."""
    ids = _scope(db, user)
    risks = latest_scores(db, ids)
    names = dict(db.execute(select(Patient.id, Patient.full_name).where(Patient.id.in_(ids))).all()) if ids else {}
    allowed = {"high"} if min_band == "high" else {"moderate", "high"}
    rows = []
    for pid, per_model in risks.items():
        for m, r in per_model.items():
            if (model and m != model) or r.band not in allowed:
                continue
            top = r.factors[0] if r.factors else None
            rows.append({"patient_id": pid, "patient_name": names.get(pid), "model": m, "score": r.score,
                         "band": r.band, "percentile": r.percentile, "computed_at": r.computed_at,
                         "top_factor": f"{top['label']}: {top['display_value']}" if top else None})
    # Raw probabilities aren't comparable across models (different base rates); band + percentile are.
    rows.sort(key=lambda x: (x["band"] == "high", x["percentile"], x["score"]), reverse=True)
    return rows[:100]


def psi(reference_percentiles: list[float], scores: list[float]) -> float | None:
    """Population Stability Index of live scores vs the validation distribution (10 equal-mass bins)."""
    if len(scores) < 20:
        return None
    edges = [reference_percentiles[i] for i in range(0, 101, 10)]
    edges[0], edges[-1] = -math.inf, math.inf
    counts = [0] * 10
    for s in scores:
        for b in range(10):
            if edges[b] <= s < edges[b + 1]:
                counts[b] += 1
                break
    total = sum(counts)
    value = 0.0
    for c in counts:
        a = max(c / total, 1e-4)
        value += (a - 0.1) * math.log(a / 0.1)
    return value


@router.get("/models")
def model_monitoring(db: DB, user: User = Depends(require_roles("admin"))):
    """Per-model drift check: are live patients scored like the population the model was validated on?"""
    out = []
    for m in available_models():
        name = m.task.name
        scores = db.scalars(select(RiskScore.score).where(RiskScore.model == name)
                            .order_by(RiskScore.computed_at.desc()).limit(5000)).all()
        value = psi(m.metadata["val_score_percentiles"], list(scores))
        out.append({
            "model": name, "title": m.metadata["title"], "version": m.version,
            "live_scores": len(scores),
            "live_mean_score": (sum(scores) / len(scores)) if scores else None,
            "reference_mean_score": m.metadata["metrics"]["test"]["mean_predicted"],
            "psi": value,
            "drift": None if value is None else "stable" if value < 0.1 else "moderate" if value < 0.25 else "significant",
            "test_roc_auc": m.metadata["metrics"]["test"]["roc_auc"],
        })
    return out

