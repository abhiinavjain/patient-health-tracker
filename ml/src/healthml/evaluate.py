"""Evaluation: discrimination, calibration, operational top-k metrics, subgroup fairness."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from .config import SEED


def core_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    y, p = np.asarray(y), np.asarray(p)
    return {
        "n": int(len(y)),
        "prevalence": float(y.mean()),
        "mean_predicted": float(p.mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-7, 1 - 1e-7))),
    }


def top_k(y: np.ndarray, p: np.ndarray, fractions=(0.05, 0.10, 0.20, 0.30)) -> list[dict[str, float]]:
    """If the team can only follow up the top X% highest-risk patients, what do they catch?"""
    y, p = np.asarray(y), np.asarray(p)
    order = np.argsort(-p, kind="stable")
    total_pos = y.sum()
    rows = []
    for f in fractions:
        k = max(1, int(round(f * len(y))))
        hits = y[order[:k]].sum()
        precision = hits / k
        rows.append({
            "fraction_flagged": f,
            "n_flagged": int(k),
            "threshold": float(p[order[k - 1]]),
            "precision": float(precision),
            "recall": float(hits / total_pos) if total_pos else float("nan"),
            "lift": float(precision / y.mean()) if y.mean() else float("nan"),
        })
    return rows


def bootstrap_ci(y: np.ndarray, p: np.ndarray, metric=roc_auc_score, n: int = 300, alpha: float = 0.05,
                 groups: np.ndarray | None = None) -> tuple[float, float]:
    """Percentile bootstrap CI. Resamples patients (groups) rather than rows when groups are given."""
    rng = np.random.default_rng(SEED)
    y, p = np.asarray(y), np.asarray(p)
    if groups is not None:
        _, inv, counts = np.unique(np.asarray(groups), return_inverse=True, return_counts=True)
        order = np.argsort(inv, kind="stable")
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    stats = []
    for _ in range(n):
        if groups is not None:
            pick = rng.integers(0, len(counts), len(counts))
            # Expand each sampled patient into all of their rows (vectorised).
            lens = counts[pick]
            offs = np.repeat(starts[pick] - np.concatenate([[0], np.cumsum(lens)[:-1]]), lens)
            idx = order[np.arange(lens.sum()) + offs]
        else:
            idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        stats.append(metric(y[idx], p[idx]))
    lo, hi = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def calibration_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=n_bins, strategy="quantile")
    return pd.DataFrame({"mean_predicted": mean_pred, "observed_rate": frac_pos})


def subgroup_report(y: np.ndarray, p: np.ndarray, subgroups: pd.DataFrame, threshold: float,
                    min_n: int = 200) -> pd.DataFrame:
    """Per-subgroup performance at a single global threshold (equal-opportunity style view)."""
    y, p = np.asarray(y), np.asarray(p)
    flagged = p >= threshold
    rows = []
    for col in subgroups.columns:
        vals = subgroups[col].to_numpy()
        for v in pd.unique(vals):
            m = vals == v
            if m.sum() < min_n or y[m].min() == y[m].max():
                continue
            pos = y[m] == 1
            rows.append({
                "attribute": col,
                "group": str(v),
                "n": int(m.sum()),
                "prevalence": float(y[m].mean()),
                "mean_predicted": float(p[m].mean()),
                "roc_auc": float(roc_auc_score(y[m], p[m])),
                "flag_rate": float(flagged[m].mean()),
                "tpr_at_threshold": float(flagged[m][pos].mean()) if pos.any() else float("nan"),
                "fpr_at_threshold": float(flagged[m][~pos].mean()) if (~pos).any() else float("nan"),
            })
    return pd.DataFrame(rows)
