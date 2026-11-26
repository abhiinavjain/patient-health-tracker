"""Inference entry point used by the API.

    model = RiskModel.load("readmission_30d")
    model.predict([{"age_years": 75, "number_inpatient": 3, ...}])
"""

from __future__ import annotations

import bisect
import json
from functools import lru_cache
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from .config import ARTIFACTS
from .explain import shap_values, top_factors
from .modeling import PlattCalibrator, to_model_frame
from .tasks import Task, get_task


class RiskModel:
    def __init__(self, task: Task, booster: lgb.Booster, metadata: dict) -> None:
        self.task = task
        self.booster = booster
        self.metadata = metadata
        self.numeric: list[str] = metadata["features"]["numeric"]
        self.categories: dict[str, list[str]] = metadata["features"]["categorical"]
        cal = metadata["calibration"]
        self.calibrator = PlattCalibrator(a=cal["a"], b=cal["b"])
        self._pcts: list[float] = metadata["val_score_percentiles"]

    @classmethod
    def load(cls, name: str, artifacts: Path | str = ARTIFACTS) -> RiskModel:
        d = Path(artifacts) / name
        metadata = json.loads((d / "metadata.json").read_text())
        booster = lgb.Booster(model_file=str(d / "model.txt"))
        return cls(get_task(name), booster, metadata)

    @property
    def version(self) -> str:
        return self.metadata["version"]

    def band(self, score: float) -> str:
        cuts = self.metadata["risk_bands"]
        return "high" if score >= cuts["high"] else "moderate" if score >= cuts["moderate"] else "low"

    def percentile(self, score: float) -> int:
        """Share of the reference (validation) population with a lower score."""
        return max(0, min(100, bisect.bisect_left(self._pcts, score) - 1))

    def predict(self, records: list[dict] | pd.DataFrame, n_factors: int = 5) -> list[dict]:
        df = records if isinstance(records, pd.DataFrame) else pd.DataFrame.from_records(records)
        X = self.task.prepare(df)
        # Unknown category values count as missing too.
        for c, levels in self.categories.items():
            X[c] = X[c].where(X[c].isin(levels), None)
        missing = X.isna()
        # Impute with training medians/modes: the training data has no gaps, so letting the trees route
        # NaNs would be arbitrary. Imputed features are excluded from the explanation.
        fill = self.metadata.get("fill_values", {})
        X = X.fillna({c: v for c, v in fill.items() if c in X.columns})
        Xm = to_model_frame(X, self.numeric, self.categories)
        scores = self.calibrator.transform(self.booster.predict(Xm))
        contrib, _ = shap_values(self.booster, Xm)
        results = []
        for i in range(len(Xm)):
            s = float(scores[i])
            miss = [c for c in self.task.features if missing.iloc[i][c]]
            results.append({
                "model": self.task.name,
                "model_version": self.version,
                "score": s,
                "band": self.band(s),
                "percentile": self.percentile(s),
                "missing_features": miss,
                "completeness": 1 - len(miss) / len(self.task.features),
                "factors": top_factors(self.task, X.iloc[i], contrib[i], k=n_factors, exclude=set(miss)),
            })
        return results


@lru_cache(maxsize=8)
def get_model(name: str) -> RiskModel:
    return RiskModel.load(name)
