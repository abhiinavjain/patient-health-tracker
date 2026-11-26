# healthml — risk models for Patient Health Tracker v2

Three calibrated, explainable risk models trained on public, de-identified data. Each is packaged as a versioned artifact that the FastAPI service loads for inference.

| Model | Question it answers | Data |
|---|---|---|
| `readmission_30d` | Will this inpatient be readmitted within 30 days of discharge? | UCI Diabetes 130-US Hospitals, ~100k encounters |
| `diabetes_risk` | Does this person's profile suggest prediabetes/diabetes (offer a test)? | CDC BRFSS 2015, 253k respondents |
| `cvd_risk` | Does this person's profile resemble coronary heart disease? | CDC BRFSS 2015 |

## Results (held-out test set)

| Model | Test rows | Prevalence | ROC-AUC (95% CI) | PR-AUC | LogReg baseline AUC | Top-10% flagged: precision / recall |
|---|---|---|---|---|---|---|
| `readmission_30d` | 14,815 | 11.1% | **0.687** (0.673–0.701) | 0.232 | 0.673 | 26.7% / 24.0% (2.4× lift) |
| `diabetes_risk` | 38,052 | 13.9% | **0.827** (0.821–0.832) | 0.420 | 0.818 | see model card |
| `cvd_risk` | 38,052 | 9.4% | **0.851** (0.845–0.857) | 0.367 | 0.848 | see model card |

All three are well calibrated after Platt scaling (Brier 0.093 / 0.098 / 0.070). Gradient boosting beats a well-built logistic regression only modestly. That's typical for these tabular datasets, and the model cards say so. Readmission AUC is in line with published results on this dataset (≈0.65–0.70).

Full results, plots and subgroup analyses: [`artifacts/readmission_30d/MODEL_CARD.md`](artifacts/readmission_30d/MODEL_CARD.md), [`artifacts/diabetes_risk/MODEL_CARD.md`](artifacts/diabetes_risk/MODEL_CARD.md), [`artifacts/cvd_risk/MODEL_CARD.md`](artifacts/cvd_risk/MODEL_CARD.md).

## Quick start

```bash
cd ml
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[train,dev]"
python -m healthml.download          # ~33 MB of public CSVs into data/raw/ (git-ignored)
python -m healthml.train --task all  # 20 Optuna trials/model; --trials 5 for a quick run (HEALTHML_THREADS to tune CPU use)
pytest                               # runs on synthetic data, no download needed
```

## Pipeline

```
download ─▶ tasks/<task>.py ─▶ split ─▶ baseline LR ─▶ LightGBM + Optuna ─▶ Platt calibration
            (cleaning +        (grouped      │               │                    │
             feature eng.)      by patient)  └──── test-set evaluation ◀──────────┘
                                                 ROC/PR-AUC + bootstrap CI, Brier, calibration,
                                                 top-k precision/recall/lift, subgroup TPR/FPR,
                                                 SHAP global importance
                                              ─▶ artifacts/<task>/ {model.txt, metadata.json, MODEL_CARD.md, figures/}
```

Methodological choices worth knowing:

- **No patient leakage.** The readmission data has repeated patients. Train, validation and test are split by `patient_nbr`, and the bootstrap CIs resample patients rather than rows.
- **Probabilities you can trust.** No class re-weighting, which keeps scores calibrated. A 2-parameter Platt scaler is fit on validation only. Brier score is reported before and after calibration.
- **Operational metrics.** "If the care team can call the top 10% of patients, what share of readmissions do they reach?" That is the number a hospital actually cares about.
- **Fairness by design.**
  - Race is excluded as an input to the readmission model, and income, education and insurance are excluded from the chronic-disease models.
  - Performance is reported per race, sex and age band at one shared threshold.
- **Explanations.** Each prediction returns its top factors using exact TreeSHAP (LightGBM `pred_contrib`). No separate explainer is needed at serving time.
- **Honest scope.** Each model card states its intended use, dataset era and population, and known limitations.

## Inference

```python
from healthml.predict import RiskModel

model = RiskModel.load("readmission_30d")
model.predict([{
    "age_years": 75, "sex": "female", "time_in_hospital": 9, "number_inpatient": 3,
    "discharge_to": "facility", "diag_1_group": "circulatory", "insulin": "up",
}])
# -> [{"score": 0.27, "band": "high", "percentile": 94, "model_version": "2.0.0+…",
#      "missing_features": [...],
#      "factors": [{"label": "Inpatient stays in past year", "display_value": "3",
#                   "direction": "increases", "impact": 0.61}, ...]}]
```

Missing inputs are allowed. They are imputed with training medians/modes (stored in `metadata.json`) and are **never shown as explanation factors**. `missing_features` and `completeness` tell the UI what to ask the patient or clinician for. Unseen category values are treated as missing. `healthml.tasks.readmission.icd10_group()` maps the app's ICD-10 codes to the diagnosis groups used in training.

## Layout

```
src/healthml/
  config.py        paths, dataset URLs
  download.py      dataset fetcher
  tasks/           one module per prediction task (cleaning, features, labels, model-card text)
  modeling.py      shared dtype handling + Platt calibrator (train == serve)
  train.py         split, baseline, tuning, calibration, packaging
  evaluate.py      metrics, bootstrap CIs, top-k, subgroup report
  explain.py       TreeSHAP factors
  report.py        figures + MODEL_CARD.md
  predict.py       RiskModel — the API's single inference entry point
tests/             synthetic-data unit + end-to-end tests
artifacts/         trained models and reports (committed; small)
```
