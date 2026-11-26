"""Per-prediction explanations using exact TreeSHAP (LightGBM pred_contrib).

Contributions are in log-odds space of the uncalibrated model. Calibration is a monotone transform, so the
direction and relative size of each factor is preserved.
"""

from __future__ import annotations

import math

import lightgbm as lgb
import numpy as np
import pandas as pd

from .tasks.base import Task


def shap_values(booster: lgb.Booster, Xm: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    contrib = booster.predict(Xm, pred_contrib=True)
    return contrib[:, :-1], contrib[:, -1]


def _fmt_value(task: Task, feature: str, value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA:
        return "not recorded"
    mapping = task.value_text.get(feature)
    if mapping is not None:
        try:
            return str(mapping.get(int(value), value))
        except (TypeError, ValueError):
            return str(mapping.get(value, value))
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value).replace("_", " ")


def top_factors(task: Task, row: pd.Series, contrib: np.ndarray, k: int = 5,
                exclude: set[str] | None = None) -> list[dict]:
    exclude = exclude or set()
    factors = []
    for i in np.argsort(-np.abs(contrib)):
        feat = task.features[i]
        if len(factors) >= k or abs(contrib[i]) < 1e-4:
            break
        if feat in exclude:
            continue
        factors.append({
            "feature": feat,
            "label": task.labels.get(feat, feat),
            "value": None if pd.isna(row[feat]) else (row[feat] if not isinstance(row[feat], np.generic) else row[feat].item()),
            "display_value": _fmt_value(task, feat, row[feat]),
            "impact": float(contrib[i]),
            "direction": "increases" if contrib[i] > 0 else "decreases",
        })
    return factors
