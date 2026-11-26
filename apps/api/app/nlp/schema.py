"""What an extractor returns: the contract between extractors, the evaluation scorer and the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..catalog import OBSERVATIONS

FrequencyCode = Literal[
    "once_daily", "twice_daily", "three_times_daily", "four_times_daily", "at_night", "as_needed", "weekly",
    "with_meals", "other",
]
MedAction = Literal["started", "continued", "dose_increased", "dose_decreased", "stopped"]
ObservationCode = Literal[tuple(OBSERVATIONS)]  # type: ignore[valid-type]

FREQUENCY_TEXT = {
    "once_daily": "once daily", "twice_daily": "twice daily", "three_times_daily": "three times daily",
    "four_times_daily": "four times daily", "at_night": "at night", "as_needed": "as needed", "weekly": "weekly",
    "with_meals": "with meals", "other": None,
}


class ExtractedCondition(BaseModel):
    icd10_code: str = Field(description="Most specific ICD-10 code supported by the note, e.g. E11.9")
    description: str
    status: Literal["active", "resolved"] = "active"
    evidence: str = Field(description="Exact quote from the note that supports this item")


class ExtractedMedication(BaseModel):
    name: str = Field(description="Generic name in lowercase; combinations joined with '-', e.g. budesonide-formoterol")
    dose: str | None = Field(default=None, description="Strength with unit, e.g. '500 mg', '10 units', '200/6 mcg'")
    frequency: FrequencyCode | None = None
    route: str | None = None
    action: MedAction
    evidence: str


class ExtractedObservation(BaseModel):
    code: ObservationCode
    value: float = Field(description="Value converted to the code's canonical unit")
    evidence: str


class NoteExtraction(BaseModel):
    conditions: list[ExtractedCondition] = []
    medications: list[ExtractedMedication] = []
    observations: list[ExtractedObservation] = []
    follow_up_days: int | None = Field(default=None, description="Days until the planned review, if stated")
