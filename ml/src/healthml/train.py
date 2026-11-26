"""Train, evaluate, explain and package a risk model.

Usage:
    python -m healthml.train --task readmission_30d
    python -m healthml.train --task all --trials 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import __version__
from .config import ARTIFACTS, SEED
from .evaluate import bootstrap_ci, calibration_table, core_metrics, subgroup_report, top_k
from .explain import shap_values
from .modeling import PlattCalibrator, to_model_frame
from .tasks import TASKS, Task, TaskData, get_task


# --------------------------------------------------------------------------- splitting
def split(data: TaskData, test_size: float = 0.15, val_size: float = 0.15):
    """Train/val/test split. Grouped by patient when the task has repeated patients, else stratified."""
    idx = np.arange(len(data.y))
    if data.groups is not None:
        g = data.groups.to_numpy()
        outer = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=SEED)
        trval, test = next(outer.split(idx, groups=g))
        inner = GroupShuffleSplit(n_splits=1, test_size=val_size / (1 - test_size), random_state=SEED)
        tr, va = next(inner.split(trval, groups=g[trval]))
        train, val = trval[tr], trval[va]
        assert not set(g[train]) & set(g[test]), "patient leakage between train and test"
    else:
        y = data.y.to_numpy()
        trval, test = train_test_split(idx, test_size=test_size, stratify=y, random_state=SEED)
        train, val = train_test_split(trval, test_size=val_size / (1 - test_size), stratify=y[trval],
                                      random_state=SEED)
    return train, val, test


# --------------------------------------------------------------------------- models
def fit_baseline(task: Task, X: pd.DataFrame, y: np.ndarray) -> Pipeline:
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), task.numeric),
        *([("cat", Pipeline([
            ("impute", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=50)),
        ]), task.categorical)] if task.categorical else []),
    ])
    model = Pipeline([("pre", pre), ("lr", LogisticRegression(max_iter=2000, C=1.0))])
    model.fit(X, y)
    return model


BASE_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "verbosity": -1,
    "seed": SEED,
    # LightGBM slows down badly when its threads compete for cores; leave headroom (≈ physical cores).
    "num_threads": int(os.environ.get("HEALTHML_THREADS", max(1, (os.cpu_count() or 4) // 2))),
    "bagging_freq": 1,
}


def _train_lgb(params, Xtr, ytr, Xva, yva, rounds=3000):
    dtr = lgb.Dataset(Xtr, ytr, free_raw_data=False)
    dva = lgb.Dataset(Xva, yva, reference=dtr, free_raw_data=False)
    return lgb.train(
        {**BASE_PARAMS, **params}, dtr, num_boost_round=rounds, valid_sets=[dva],
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )


def tune_lgb(Xtr, ytr, Xva, yva, n_trials: int) -> tuple[dict, lgb.Booster, list[dict]]:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    history: list[dict] = []

    def objective(trial: optuna.Trial) -> float:
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, 128, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 400, log=True),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-3, 30.0, log=True),
            "cat_smooth": trial.suggest_float("cat_smooth", 1.0, 50.0, log=True),
        }
        booster = _train_lgb(params, Xtr, ytr, Xva, yva)
        ap = average_precision_score(yva, booster.predict(Xva, num_iteration=booster.best_iteration))
        trial.set_user_attr("best_iteration", booster.best_iteration)
        history.append({"trial": trial.number, "val_pr_auc": ap, "best_iteration": booster.best_iteration, **params})
        return ap

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    best = study.best_params
    rounds = study.best_trial.user_attrs["best_iteration"]
    final = lgb.train({**BASE_PARAMS, **best}, lgb.Dataset(Xtr, ytr), num_boost_round=rounds)
    return {**best, "num_boost_round": rounds}, final, history


# --------------------------------------------------------------------------- orchestration
def _sha256(path: str) -> str:
    if not path or not Path(path).exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def run(task_name: str, n_trials: int = 30, out_root: Path = ARTIFACTS, data: TaskData | None = None,
        make_report: bool = True) -> dict:
    t0 = time.time()
    task = get_task(task_name)
    print(f"\n=== {task.title} ({task.name}) ===")
    data = data if data is not None else task.load()
    y = data.y.to_numpy()
    print(f"rows={len(y):,}  positives={y.mean():.2%}  features={len(task.features)}")

    tr, va, te = split(data)
    categories = {c: sorted(data.X[c].dropna().astype(str).unique().tolist()) for c in task.categorical}
    Xm = to_model_frame(data.X, task.numeric, categories)
    Xtr, Xva, Xte = Xm.iloc[tr], Xm.iloc[va], Xm.iloc[te]
    ytr, yva, yte = y[tr], y[va], y[te]
    print(f"split: train={len(tr):,} val={len(va):,} test={len(te):,}")

    # Baseline
    base = fit_baseline(task, data.X.iloc[tr], ytr)
    p_base = base.predict_proba(data.X.iloc[te])[:, 1]
    base_metrics = core_metrics(yte, p_base)
    print(f"baseline LR   test ROC-AUC={base_metrics['roc_auc']:.4f}  PR-AUC={base_metrics['pr_auc']:.4f}")

    # LightGBM + tuning
    params, booster, history = tune_lgb(Xtr, ytr, Xva, yva, n_trials)
    p_val_raw = booster.predict(Xva)
    calibrator = PlattCalibrator.fit(p_val_raw, yva)
    p_te_raw = booster.predict(Xte)
    p_te = calibrator.transform(p_te_raw)
    raw_metrics = core_metrics(yte, p_te_raw)
    metrics = core_metrics(yte, p_te)
    groups_te = data.groups.to_numpy()[te] if data.groups is not None else None
    metrics["roc_auc_ci95"] = bootstrap_ci(yte, p_te, groups=groups_te)
    metrics["pr_auc_ci95"] = bootstrap_ci(yte, p_te, metric=average_precision_score, groups=groups_te)
    print(f"LightGBM      test ROC-AUC={metrics['roc_auc']:.4f} {metrics['roc_auc_ci95']}  "
          f"PR-AUC={metrics['pr_auc']:.4f}  Brier raw={raw_metrics['brier']:.4f} cal={metrics['brier']:.4f}")

    # Operating points & risk bands from the validation distribution (never the test set).
    p_val = calibrator.transform(p_val_raw)
    band_cuts = {"moderate": float(np.quantile(p_val, 0.70)), "high": float(np.quantile(p_val, 0.90))}
    percentiles = np.quantile(p_val, np.linspace(0, 1, 101)).tolist()
    topk = top_k(yte, p_te)
    subgroups = subgroup_report(yte, p_te, data.subgroups.iloc[te].reset_index(drop=True), band_cuts["high"])
    calib = calibration_table(yte, p_te)

    # Global explanations on a sample of the test set
    sample = Xte.sample(min(5000, len(Xte)), random_state=SEED)
    sv, _ = shap_values(booster, sample)
    importance = (pd.DataFrame({"feature": task.features, "mean_abs_shap": np.abs(sv).mean(axis=0)})
                  .sort_values("mean_abs_shap", ascending=False))
    importance["label"] = importance["feature"].map(task.labels)

    out = Path(out_root) / task.name
    (out / "figures").mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out / "model.txt"))

    metadata = {
        "name": task.name,
        "title": task.title,
        "version": f"{__version__}+{datetime.now(timezone.utc):%Y%m%d}",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": task.target_description,
        "dataset": task.dataset,
        "data_sha256": _sha256(data.source_csv),
        "n_rows": int(len(y)),
        "split": {"train": int(len(tr)), "val": int(len(va)), "test": int(len(te)),
                  "grouped_by_patient": data.groups is not None},
        "features": {"numeric": task.numeric, "categorical": categories},
        "labels": task.labels,
        # Used at inference to impute inputs the app doesn't have (training data has none missing).
        "fill_values": {
            **{c: float(data.X[c].iloc[tr].median()) for c in task.numeric},
            **{c: str(data.X[c].iloc[tr].mode().iloc[0]) for c in task.categorical},
        },
        "calibration": {"method": "platt", "a": calibrator.a, "b": calibrator.b},
        "risk_bands": band_cuts,
        "val_score_percentiles": percentiles,
        "params": params,
        "metrics": {"test": metrics, "test_uncalibrated": raw_metrics, "baseline_logreg_test": base_metrics},
        "top_k": topk,
    }
    (out / "metadata.json").write_text(json.dumps(_jsonable(metadata), indent=2))
    subgroups.to_csv(out / "subgroups.csv", index=False)
    importance.to_csv(out / "feature_importance.csv", index=False)
    calib.to_csv(out / "calibration.csv", index=False)
    pd.DataFrame(history).to_csv(out / "tuning_history.csv", index=False)

    if make_report:
        from .report import write_report

        write_report(task, metadata, subgroups, importance, calib, out,
                     y_test=yte, p_test=p_te, p_base=p_base, shap_sample=sample, shap_matrix=sv)

    _log_mlflow(task, metadata, out)
    print(f"artifacts -> {out}  ({time.time() - t0:.0f}s)")
    return metadata


def _log_mlflow(task: Task, metadata: dict, out: Path) -> None:
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_experiment("patient-health-tracker")
    with mlflow.start_run(run_name=task.name):
        mlflow.log_params({k: v for k, v in metadata["params"].items()})
        test = metadata["metrics"]["test"]
        mlflow.log_metrics({k: v for k, v in test.items() if isinstance(v, (int, float))})
        mlflow.log_artifacts(str(out))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", default="all", choices=["all", *TASKS])
    parser.add_argument("--trials", type=int, default=20, help="Optuna trials per task")
    parser.add_argument("--out", type=Path, default=ARTIFACTS)
    args = parser.parse_args()
    names = list(TASKS) if args.task == "all" else [args.task]
    for name in names:
        run(name, n_trials=args.trials, out_root=args.out)


if __name__ == "__main__":
    main()
