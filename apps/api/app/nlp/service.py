"""Turn a free-text note into a *draft* consultation for clinician review. Nothing is written to the record here.

Pipeline: local extraction (runs on this server; no note text leaves it) -> grounding check -> plausibility/format
validation -> reconcile against the patient's problem and medication lists -> EncounterIn-compatible draft + review list.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from ..catalog import OBSERVATIONS
from ..models import Patient
from ..schemas import ConditionIn, MedicationIn, ObservationIn
from .normalize import med_key
from .local import LocalExtractor
from .schema import FREQUENCY_TEXT, NoteExtraction

log = logging.getLogger(__name__)

# Physiologically plausible ranges; anything outside is almost certainly a parsing error.
PLAUSIBLE = {
    "bp_systolic": (50, 300), "bp_diastolic": (20, 200), "heart_rate": (20, 250), "spo2": (50, 100),
    "temperature": (30, 45), "weight": (1, 400), "height": (40, 250), "bmi": (8, 90), "hba1c": (3, 20),
    "glucose_fasting": (20, 1000), "glucose_random": (20, 1500), "glucose_postprandial": (20, 1500), "cholesterol_total": (50, 700), "ldl": (10, 500),
    "hdl": (5, 200), "triglycerides": (20, 5000), "creatinine": (0.1, 25), "egfr": (1, 200), "hemoglobin": (2, 25),
}
ICD10 = re.compile(r"^[A-Z][0-9][0-9A-Z](\.?[0-9A-Z]{1,4})?$")


class ReviewItem(BaseModel):
    kind: Literal["condition", "medication", "observation", "follow_up"]
    label: str
    evidence: str | None = None
    status: Literal["new", "already_recorded", "dropped"]
    reason: str | None = None


class EncounterDraft(BaseModel):
    conditions: list[ConditionIn] = []
    observations: list[ObservationIn] = []
    medications: list[MedicationIn] = []
    stop_medication_ids: list[uuid.UUID] = []
    follow_up_date: date | None = None


class ExtractionResult(BaseModel):
    extractor: str
    draft: EncounterDraft
    review: list[ReviewItem]
    warnings: list[str] = []


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def grounded(evidence: str, note: str) -> bool:
    return bool(evidence) and _norm(evidence) in _norm(note)


_EXTRACTOR: LocalExtractor | None = None


def get_extractor() -> LocalExtractor:
    global _EXTRACTOR
    if _EXTRACTOR is None:
        _EXTRACTOR = LocalExtractor()
    return _EXTRACTOR


def build_draft(note: str, extraction: NoteExtraction, patient: Patient | None, visit_date: date,
                check_grounding: bool = True) -> tuple[EncounterDraft, list[ReviewItem], list[str]]:
    draft, review, warnings = EncounterDraft(), [], []

    def ungrounded(evidence: str) -> bool:
        return check_grounding and not grounded(evidence, note)

    # ---------------------------------------------------------------- conditions
    existing_cats = {c.icd10_code.upper().replace(".", "")[:3]
                     for c in (patient.conditions if patient else []) if c.status == "active" and c.category == "problem"}
    seen = set()
    for c in extraction.conditions:
        code = c.icd10_code.strip().upper()
        label = f"{code} {c.description}"
        if ungrounded(c.evidence):
            review.append(ReviewItem(kind="condition", label=label, evidence=c.evidence, status="dropped",
                                     reason="Evidence quote not found in the note"))
            continue
        if not ICD10.match(code):
            review.append(ReviewItem(kind="condition", label=label, evidence=c.evidence, status="dropped",
                                     reason="Not a valid ICD-10 code"))
            continue
        cat = code.replace(".", "")[:3]
        if cat in seen:
            continue
        seen.add(cat)
        if cat in existing_cats:
            review.append(ReviewItem(kind="condition", label=label, evidence=c.evidence, status="already_recorded",
                                     reason="Already on the problem list"))
            continue
        draft.conditions.append(ConditionIn(icd10_code=code, description=c.description, status=c.status))
        review.append(ReviewItem(kind="condition", label=label, evidence=c.evidence, status="new"))

    # ---------------------------------------------------------------- observations
    for o in extraction.observations:
        label_txt, unit, _ = OBSERVATIONS[o.code]
        label = f"{label_txt}: {o.value:g} {unit}"
        lo, hi = PLAUSIBLE.get(o.code, (float("-inf"), float("inf")))
        if ungrounded(o.evidence):
            review.append(ReviewItem(kind="observation", label=label, evidence=o.evidence, status="dropped",
                                     reason="Evidence quote not found in the note"))
        elif not lo <= o.value <= hi:
            review.append(ReviewItem(kind="observation", label=label, evidence=o.evidence, status="dropped",
                                     reason=f"Outside plausible range {lo:g}–{hi:g} {unit}"))
        else:
            draft.observations.append(ObservationIn(code=o.code, value=o.value, unit=unit))
            review.append(ReviewItem(kind="observation", label=label, evidence=o.evidence, status="new"))

    # ---------------------------------------------------------------- medications (reconciled)
    active = {}
    for m in (patient.medications if patient else []):
        if m.status == "active":
            active.setdefault(med_key(m.name), m)
    for m in extraction.medications:
        name = m.name.strip()
        label = " ".join(filter(None, [m.action.replace("_", " ").capitalize() + ":", name, m.dose,
                                       FREQUENCY_TEXT.get(m.frequency or "", None)]))
        if ungrounded(m.evidence):
            review.append(ReviewItem(kind="medication", label=label, evidence=m.evidence, status="dropped",
                                     reason="Evidence quote not found in the note"))
            continue
        current = active.get(med_key(name))
        if m.action == "continued" and current is not None:
            review.append(ReviewItem(kind="medication", label=label, evidence=m.evidence, status="already_recorded",
                                     reason="Already on the active medication list"))
            continue
        if m.action == "stopped":
            if current is not None:
                draft.stop_medication_ids.append(current.id)
                review.append(ReviewItem(kind="medication", label=label, evidence=m.evidence, status="new",
                                         reason=f"Will stop the active '{current.name}' entry"))
            else:
                review.append(ReviewItem(kind="medication", label=label, evidence=m.evidence, status="already_recorded",
                                         reason="Not on the active medication list — nothing to stop"))
            continue
        if m.action in ("dose_increased", "dose_decreased") and current is not None:
            draft.stop_medication_ids.append(current.id)  # replace the old dose with the new one
        draft.medications.append(MedicationIn(name=name, dose=m.dose, frequency=FREQUENCY_TEXT.get(m.frequency or "", None),
                                              route=m.route, action=m.action))
        review.append(ReviewItem(kind="medication", label=label, evidence=m.evidence, status="new"))

    # ---------------------------------------------------------------- follow-up
    if extraction.follow_up_days is not None:
        if 0 < extraction.follow_up_days <= 730:
            draft.follow_up_date = visit_date + timedelta(days=extraction.follow_up_days)
            review.append(ReviewItem(kind="follow_up", label=f"Follow-up in {extraction.follow_up_days} days "
                                                            f"({draft.follow_up_date.isoformat()})", status="new"))
        else:
            warnings.append(f"Ignored implausible follow-up interval of {extraction.follow_up_days} days.")

    dropped = sum(r.status == "dropped" for r in review)
    if dropped:
        warnings.append(f"{dropped} extracted item(s) were dropped by validation — see the review list.")
    return draft, review, warnings


def extract_note(note: str, patient: Patient | None = None, visit_date: date | None = None) -> ExtractionResult:
    ex = get_extractor()
    draft, review, warnings = build_draft(note, ex.extract(note), patient, visit_date or date.today())
    return ExtractionResult(extractor=ex.version, draft=draft, review=review, warnings=warnings)
