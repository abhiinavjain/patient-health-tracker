"""Common interface every prediction task implements."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TaskData:
    X: pd.DataFrame
    y: pd.Series
    # Patient identifier for group-aware splitting (None = rows are independent people).
    groups: pd.Series | None
    # Columns used only for fairness/subgroup reporting, never as model inputs.
    subgroups: pd.DataFrame
    source_csv: str = ""


@dataclass
class Task:
    name: str
    title: str
    target_description: str
    dataset: str
    numeric: list[str]
    categorical: list[str]
    labels: dict[str, str]
    # Human-friendly rendering of a few values in explanations (feature -> {value: text}).
    value_text: dict[str, dict] = field(default_factory=dict)
    intended_use: str = ""
    limitations: list[str] = field(default_factory=list)

    @property
    def features(self) -> list[str]:
        return self.numeric + self.categorical

    def load(self) -> TaskData:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def prepare(self, records: pd.DataFrame) -> pd.DataFrame:
        """Turn app-side records (already in model feature space) into a model-ready frame."""
        missing = [c for c in self.features if c not in records.columns]
        if missing:
            records = records.copy()
            for c in missing:
                records[c] = pd.NA
        out = records[self.features].copy()
        for c in self.numeric:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
        return out
