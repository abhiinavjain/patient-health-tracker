"""Score a patient with every model and persist the results."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from healthml.config import ARTIFACTS
from healthml.predict import RiskModel

from ..config import get_settings
from ..models import Patient, RiskScore
from ..schemas import RiskResult
from .features import BUILDERS

log = logging.getLogger(__name__)

MODEL_NAMES = list(BUILDERS)
MIN_COMPLETENESS = 0.5


def artifacts_dir() -> Path:
    return Path(get_settings().healthml_artifacts or ARTIFACTS)


@lru_cache(maxsize=None)
def load_model(name: str) -> RiskModel:
    return RiskModel.load(name, artifacts_dir())


def available_models() -> list[RiskModel]:
    out = []
    for name in MODEL_NAMES:
        try:
            out.append(load_model(name))
        except FileNotFoundError:
            log.warning("Model artifact missing: %s", name)
    return out


def score_patient(patient: Patient, now: datetime | None = None) -> list[RiskResult]:
    now = now or datetime.now(timezone.utc)
    results = []
    for name, builder in BUILDERS.items():
        try:
            model = load_model(name)
        except FileNotFoundError:
            continue
        built = builder(patient, now)
        base = {"model": name, "title": model.metadata["title"], "model_version": model.version,
                "encounter_id": built.encounter_id, "computed_at": now}
        if built.status != "scored":
            results.append(RiskResult(status=built.status, reason=built.reason, **base))
            continue
        pred = model.predict([built.features])[0]
        labels = model.task.labels
        missing = [labels.get(f, f) for f in pred["missing_features"]]
        if pred["completeness"] < MIN_COMPLETENESS:
            results.append(RiskResult(status="insufficient_data", completeness=pred["completeness"],
                                      missing_inputs=missing,
                                      reason="Too few inputs recorded for a reliable score.", **base))
            continue
        results.append(RiskResult(
            status="scored", score=pred["score"], band=pred["band"], percentile=pred["percentile"],
            completeness=pred["completeness"], factors=pred["factors"], missing_inputs=missing, **base,
        ))
    return results


def score_and_store(db: Session, patient: Patient) -> list[RiskResult]:
    results = score_patient(patient)
    for r in results:
        if r.status == "scored":
            db.add(RiskScore(
                patient_id=patient.id, encounter_id=r.encounter_id, model=r.model, model_version=r.model_version,
                score=r.score, band=r.band, percentile=r.percentile,
                factors=[f.model_dump() for f in r.factors], missing_features=r.missing_inputs,
                computed_at=r.computed_at,
            ))
    return results


def latest_scores(db: Session, patient_ids: list) -> dict:
    """{patient_id: {model: RiskScore}} for the most recent score of each model."""
    if not patient_ids:
        return {}
    rows = db.scalars(select(RiskScore).where(RiskScore.patient_id.in_(patient_ids))
                      .order_by(RiskScore.computed_at)).all()
    out: dict = {}
    for r in rows:  # later rows overwrite earlier ones
        out.setdefault(r.patient_id, {})[r.model] = r
    return out
