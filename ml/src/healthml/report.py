"""Figures and a Markdown model card for each trained model."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from .config import DATASETS  # noqa: E402
from .tasks.base import Task  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, ORANGE = "#2563eb", "#9ca3af", "#ea580c"


def _curves(y, p, p_base, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4))
    for probs, name, color in [(p, "LightGBM (calibrated)", BLUE), (p_base, "Logistic regression", GREY)]:
        fpr, tpr, _ = roc_curve(y, probs)
        axes[0].plot(fpr, tpr, color=color, label=name, lw=1.6)
        prec, rec, _ = precision_recall_curve(y, probs)
        axes[1].plot(rec, prec, color=color, label=name, lw=1.6)
    axes[0].plot([0, 1], [0, 1], ls="--", color="#d1d5db", lw=1)
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC")
    axes[1].axhline(np.mean(y), ls="--", color="#d1d5db", lw=1, label="Prevalence")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision–recall")
    axes[1].legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _calibration(calib: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(3.8, 3.4))
    hi = max(calib["mean_predicted"].max(), calib["observed_rate"].max()) * 1.05
    ax.plot([0, hi], [0, hi], ls="--", color="#d1d5db", lw=1)
    ax.plot(calib["mean_predicted"], calib["observed_rate"], marker="o", color=BLUE, lw=1.6, ms=4)
    ax.set(xlabel="Predicted risk (decile mean)", ylabel="Observed rate", title="Calibration (test)",
           xlim=(0, hi), ylim=(0, hi))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _importance(importance: pd.DataFrame, path: Path, k: int = 15) -> None:
    top = importance.head(k).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 0.28 * len(top) + 0.8))
    ax.barh(top["label"].fillna(top["feature"]), top["mean_abs_shap"], color=BLUE)
    ax.set(xlabel="Mean |SHAP| (log-odds)", title="Global feature importance")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _beeswarm(shap_sample: pd.DataFrame, shap_matrix: np.ndarray, task: Task, path: Path) -> None:
    try:
        import shap
    except ImportError:
        return
    X = shap_sample.copy()
    for c in task.categorical:  # shap's colouring needs numbers
        X[c] = X[c].cat.codes.replace(-1, np.nan)
    X.columns = [task.labels.get(c, c) for c in X.columns]
    shap.summary_plot(shap_matrix, X, show=False, max_display=15, plot_size=(7, 5))
    plt.title("SHAP summary (test sample)")
    plt.tight_layout()
    plt.savefig(path)
    plt.close("all")


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def write_report(task: Task, md: dict, subgroups: pd.DataFrame, importance: pd.DataFrame, calib: pd.DataFrame,
                 out: Path, *, y_test, p_test, p_base, shap_sample, shap_matrix) -> None:
    fig = out / "figures"
    _curves(y_test, p_test, p_base, fig / "roc_pr.png")
    _calibration(calib, fig / "calibration.png")
    _importance(importance, fig / "importance.png")
    _beeswarm(shap_sample, shap_matrix, task, fig / "shap_summary.png")

    t = md["metrics"]["test"]
    b = md["metrics"]["baseline_logreg_test"]
    u = md["metrics"]["test_uncalibrated"]
    ds = DATASETS[task.dataset]
    lines = [
        f"# Model card — {task.title}",
        "",
        f"`{md['name']}` · version `{md['version']}` · trained {md['trained_at']}",
        "",
        "## Intended use",
        task.intended_use,
        "",
        f"**Target:** {task.target_description}",
        "",
        "## Data",
        f"- Source: {ds['citation']}",
        f"- Rows after cleaning: {md['n_rows']:,} · prevalence {_pct(t['prevalence'])} (test)",
        f"- Split: train {md['split']['train']:,} / val {md['split']['val']:,} / test {md['split']['test']:,}"
        + (" — **grouped by patient** (no patient in more than one split)" if md["split"]["grouped_by_patient"]
           else " — stratified by outcome"),
        f"- Data file SHA-256: `{md['data_sha256'][:16]}…`",
        "",
        "## Model",
        f"LightGBM gradient-boosted trees, {len(task.features)} features, hyper-parameters tuned with Optuna "
        "(TPE) on validation PR-AUC, early stopping on validation log-loss, Platt-scaled on the validation set.",
        "",
        "## Test-set performance",
        "",
        "| Metric | Logistic regression | LightGBM (uncalibrated) | **LightGBM (calibrated)** |",
        "|---|---|---|---|",
        f"| ROC-AUC | {b['roc_auc']:.3f} | {u['roc_auc']:.3f} | **{t['roc_auc']:.3f}** "
        f"(95% CI {t['roc_auc_ci95'][0]:.3f}–{t['roc_auc_ci95'][1]:.3f}) |",
        f"| PR-AUC | {b['pr_auc']:.3f} | {u['pr_auc']:.3f} | **{t['pr_auc']:.3f}** "
        f"(95% CI {t['pr_auc_ci95'][0]:.3f}–{t['pr_auc_ci95'][1]:.3f}) |",
        f"| Brier score | {b['brier']:.4f} | {u['brier']:.4f} | **{t['brier']:.4f}** |",
        f"| Log-loss | {b['log_loss']:.4f} | {u['log_loss']:.4f} | **{t['log_loss']:.4f}** |",
        "",
        f"PR-AUC should be read against the base rate of {_pct(t['prevalence'])} (a random model scores ≈ the base rate).",
        "",
        "![ROC and PR curves](figures/roc_pr.png)",
        "",
        "### Operational view — flagging the highest-risk patients",
        "",
        "| Flag top | Patients flagged | Precision | Recall (share of all events caught) | Lift vs. random |",
        "|---|---|---|---|---|",
    ]
    for r in md["top_k"]:
        lines.append(f"| {_pct(r['fraction_flagged'])} | {r['n_flagged']:,} | {_pct(r['precision'])} | "
                     f"{_pct(r['recall'])} | {r['lift']:.2f}× |")
    lines += [
        "",
        "## Calibration",
        "Predicted risk vs. observed event rate by decile on the test set. Risk bands used in the app are cut "
        f"on the validation distribution: **moderate** ≥ {_pct(md['risk_bands']['moderate'])}, "
        f"**high** ≥ {_pct(md['risk_bands']['high'])} (top 30% / top 10%).",
        "",
        "![Calibration](figures/calibration.png)",
        "",
        "## What drives predictions",
        "",
        "![SHAP summary](figures/shap_summary.png)",
        "",
        "![Importance](figures/importance.png)",
        "",
        "## Subgroup performance",
        f"Evaluated at the single global **high-risk** threshold ({_pct(md['risk_bands']['high'])}). "
        "Groups with fewer than 200 test rows are omitted. "
        + ("Race is **not** a model input; it is reported here only to check for disparate performance."
           if "race" in set(subgroups.get("attribute", [])) else ""),
        "",
        "| Attribute | Group | n | Prevalence | Mean predicted | ROC-AUC | Flag rate | TPR | FPR |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in subgroups.iterrows():
        lines.append(f"| {r['attribute']} | {r['group']} | {r['n']:,} | {_pct(r['prevalence'])} | "
                     f"{_pct(r['mean_predicted'])} | {r['roc_auc']:.3f} | {_pct(r['flag_rate'])} | "
                     f"{_pct(r['tpr_at_threshold'])} | {_pct(r['fpr_at_threshold'])} |")
    lines += ["", "## Limitations", *[f"- {x}" for x in task.limitations],
              "- Not a medical device. Outputs are decision support for qualified clinicians.", ""]
    (out / "MODEL_CARD.md").write_text("\n".join(lines))
