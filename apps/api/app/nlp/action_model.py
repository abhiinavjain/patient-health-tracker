"""Trained medication-action classifier (started / continued / dose_increased / dose_decreased / stopped).

TF-IDF (word + character n-grams) over the text around a medication mention, logistic regression on top.
Trained by `python -m app.nlp.train_action`; the artifact is small and committed. If it is missing, the local
extractor falls back to its rules.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).with_name("models") / "action_clf.joblib"


class ActionModel:
    def __init__(self, pipeline, min_confidence: float = 0.0, mode: str = "hybrid") -> None:
        self.pipeline = pipeline
        self.min_confidence = min_confidence
        self.mode = mode

    def predict(self, context: str) -> str | None:
        proba = self.pipeline.predict_proba([context])[0]
        i = int(proba.argmax())
        return str(self.pipeline.classes_[i]) if proba[i] >= self.min_confidence else None


@lru_cache(maxsize=1)
def load_action_model(path: Path = MODEL_PATH) -> ActionModel | None:
    if not path.exists():
        return None
    bundle = joblib.load(path)
    return ActionModel(bundle["pipeline"], bundle.get("min_confidence", 0.0), bundle.get("mode", "hybrid"))
