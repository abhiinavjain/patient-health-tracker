"""Acute "at risk right now" assessment from the latest vitals and labs.

Deliberately rule-based, not ML: these thresholds are validated, explainable and what hospitals use for escalation.
Sources:
  * NEWS2 — Royal College of Physicians, National Early Warning Score 2 (2017). Aggregate >=7 = high (emergency
    response), 5-6 = medium (urgent review), a single parameter scoring 3 = urgent review, 1-4 = low.
    The app records no consciousness level (AVPU) or supplemental-oxygen flag, so the score is computed from the
    parameters present and flagged as partial.
  * Hypoglycaemia levels — ADA Standards of Care: level 2 < 54 mg/dL (clinically significant), level 1 < 70 mg/dL.
  * Hypertensive crisis — 2017 ACC/AHA guideline: >= 180/120 mmHg needs prompt evaluation; we treat >= 220 systolic or
    >= 130 diastolic as critical.
  * Other critical lab values follow common laboratory critical-value lists (e.g. haemoglobin < 7 g/dL).
This is decision support: every alert is reviewed by a clinician before a patient sees it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..catalog import OBSERVATIONS
from ..models import Observation

LEVELS = ("normal", "watch", "urgent", "critical")
RECENT = timedelta(hours=24)  # readings within 24 h of the newest one count as "current"


@dataclass
class Reason:
    code: str
    label: str
    value: float
    unit: str
    severity: str  # watch | urgent | critical
    rule: str


@dataclass
class Assessment:
    level: str = "normal"
    news2: int | None = None
    news2_partial: bool = True
    reasons: list[Reason] = field(default_factory=list)

    def bump(self, level: str) -> None:
        if LEVELS.index(level) > LEVELS.index(self.level):
            self.level = level


def _band(value: float, bands: list[tuple[float, int]]) -> int:
    """bands: (upper bound inclusive, points), ascending; the last band catches everything above."""
    for upper, points in bands:
        if value <= upper:
            return points
    return bands[-1][1]


NEWS2 = {
    "respiratory_rate": [(8, 3), (11, 1), (20, 0), (24, 2), (float("inf"), 3)],
    "spo2": [(91, 3), (93, 2), (95, 1), (float("inf"), 0)],
    "bp_systolic": [(90, 3), (100, 2), (110, 1), (219, 0), (float("inf"), 3)],
    "heart_rate": [(40, 3), (50, 1), (90, 0), (110, 1), (130, 2), (float("inf"), 3)],
    "temperature": [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1), (float("inf"), 2)],
}

# (code, test, severity, rule text) — checked independently of NEWS2.
CRITICAL_VALUES = [
    ("bp_systolic", lambda v: v >= 220, "critical", "Systolic BP ≥ 220 mmHg (hypertensive crisis)"),
    ("bp_diastolic", lambda v: v >= 130, "critical", "Diastolic BP ≥ 130 mmHg (hypertensive crisis)"),
    ("bp_systolic", lambda v: 180 <= v < 220, "urgent", "Systolic BP ≥ 180 mmHg (severe hypertension)"),
    ("bp_diastolic", lambda v: 120 <= v < 130, "urgent", "Diastolic BP ≥ 120 mmHg (severe hypertension)"),
    ("spo2", lambda v: v < 90, "critical", "Oxygen saturation < 90%"),
    ("heart_rate", lambda v: v >= 150 or v <= 40, "critical", "Heart rate ≥ 150 or ≤ 40 bpm"),
    ("temperature", lambda v: v >= 40.0, "critical", "Temperature ≥ 40 °C"),
    ("glucose_fasting", lambda v: v < 54, "critical", "Glucose < 54 mg/dL (level 2 hypoglycaemia)"),
    ("glucose_random", lambda v: v < 54, "critical", "Glucose < 54 mg/dL (level 2 hypoglycaemia)"),
    ("glucose_postprandial", lambda v: v < 54, "critical", "Glucose < 54 mg/dL (level 2 hypoglycaemia)"),
    ("glucose_fasting", lambda v: 54 <= v < 70, "urgent", "Glucose < 70 mg/dL (hypoglycaemia)"),
    ("glucose_random", lambda v: 54 <= v < 70, "urgent", "Glucose < 70 mg/dL (hypoglycaemia)"),
    ("glucose_random", lambda v: v >= 400, "critical", "Glucose ≥ 400 mg/dL (severe hyperglycaemia)"),
    ("glucose_postprandial", lambda v: v >= 400, "critical", "Glucose ≥ 400 mg/dL (severe hyperglycaemia)"),
    ("glucose_fasting", lambda v: v >= 300, "critical", "Fasting glucose ≥ 300 mg/dL (severe hyperglycaemia)"),
    ("glucose_random", lambda v: 300 <= v < 400, "urgent", "Glucose ≥ 300 mg/dL"),
    ("glucose_postprandial", lambda v: 300 <= v < 400, "urgent", "Glucose ≥ 300 mg/dL"),
    ("hemoglobin", lambda v: v < 7, "critical", "Haemoglobin < 7 g/dL"),
    ("hemoglobin", lambda v: 7 <= v < 8, "urgent", "Haemoglobin < 8 g/dL"),
    ("egfr", lambda v: v < 15, "urgent", "eGFR < 15 (kidney failure range)"),
    ("creatinine", lambda v: v >= 4, "urgent", "Creatinine ≥ 4 mg/dL"),
]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def current_readings(observations: list[Observation]) -> dict[str, Observation]:
    """Latest reading per code, limited to the 24 h before the newest reading."""
    if not observations:
        return {}
    newest = max(_aware(o.observed_at) for o in observations)
    latest: dict[str, Observation] = {}
    for o in sorted(observations, key=lambda o: _aware(o.observed_at)):
        if newest - _aware(o.observed_at) <= RECENT:
            latest[o.code] = o
    return latest


def assess(observations: list[Observation]) -> Assessment:
    current = current_readings(observations)
    a = Assessment()

    def reason(code: str, severity: str, rule: str) -> Reason:
        o = current[code]
        return Reason(code=code, label=OBSERVATIONS[code][0], value=o.value, unit=o.unit, severity=severity, rule=rule)

    # NEWS2 from whatever parameters are present
    scored = {c: _band(current[c].value, bands) for c, bands in NEWS2.items() if c in current}
    if scored:
        a.news2 = sum(scored.values())
        a.news2_partial = True  # AVPU and the supplemental-oxygen flag are never recorded
        if a.news2 >= 7:
            a.bump("critical")
        elif a.news2 >= 5 or 3 in scored.values():
            a.bump("urgent")
        elif a.news2 >= 1:
            a.bump("watch")
        for c, pts in scored.items():
            if pts >= 2:
                a.reasons.append(reason(c, "urgent" if pts == 3 else "watch", f"NEWS2: {pts} points"))

    for code, test, severity, rule in CRITICAL_VALUES:
        if code in current and test(current[code].value):
            a.bump(severity)
            a.reasons = [r for r in a.reasons if r.code != code] + [reason(code, severity, rule)]

    order = {"critical": 0, "urgent": 1, "watch": 2}
    a.reasons.sort(key=lambda r: order[r.severity])
    return a
