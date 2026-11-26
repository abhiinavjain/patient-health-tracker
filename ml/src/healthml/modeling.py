"""Pieces shared by training and inference so both see identical inputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def to_model_frame(X: pd.DataFrame, numeric: list[str], categories: dict[str, list[str]]) -> pd.DataFrame:
    """Fix dtypes and categorical levels. Unseen category values become missing (NaN)."""
    out = pd.DataFrame(index=X.index)
    for c in numeric:
        out[c] = pd.to_numeric(X[c], errors="coerce").astype("float64")
    for c, levels in categories.items():
        vals = X[c].astype("object")
        vals = vals.where(vals.isin(levels), None)
        out[c] = pd.Categorical(vals, categories=levels)
    return out


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


@dataclass
class PlattCalibrator:
    """p_cal = sigmoid(a * logit(p_raw) + b). Two parameters, so it barely overfits the validation set."""

    a: float = 1.0
    b: float = 0.0

    @classmethod
    def fit(cls, p_raw: np.ndarray, y: np.ndarray) -> PlattCalibrator:
        from sklearn.linear_model import LogisticRegression

        lr = LogisticRegression(C=1e6, max_iter=1000)
        lr.fit(_logit(p_raw).reshape(-1, 1), y)
        return cls(a=float(lr.coef_[0, 0]), b=float(lr.intercept_[0]))

    def transform(self, p_raw: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-(self.a * _logit(np.asarray(p_raw)) + self.b)))
