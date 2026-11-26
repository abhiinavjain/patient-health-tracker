"""Synthetic stand-ins for the raw UCI files so the pipeline is testable without downloads."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from healthml.tasks.readmission import MEDICATIONS


@pytest.fixture(scope="session")
def raw_readmission() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 4000
    patients = rng.integers(0, 2500, n)
    inpatient = rng.poisson(0.6, n)
    logit = -2.3 + 0.5 * inpatient + rng.normal(0, 0.5, n)
    readmit = rng.random(n) < 1 / (1 + np.exp(-logit))
    df = pd.DataFrame({
        "encounter_id": np.arange(n) * 7 + 100,
        "patient_nbr": patients,
        "race": rng.choice(["Caucasian", "AfricanAmerican", "?"], n),
        "gender": rng.choice(["Male", "Female", "Unknown/Invalid"], n, p=[0.48, 0.5, 0.02]),
        "age": rng.choice([f"[{a}-{a + 10})" for a in range(0, 100, 10)], n),
        "weight": "?",
        "admission_type_id": rng.choice([1, 2, 3, 5, 6], n),
        "discharge_disposition_id": rng.choice([1, 3, 6, 11, 13, 18], n),
        "admission_source_id": rng.choice([1, 4, 7, 9], n),
        "time_in_hospital": rng.integers(1, 14, n),
        "payer_code": "?",
        "medical_specialty": rng.choice(["InternalMedicine", "Cardiology", "Podiatry", "?"], n),
        "num_lab_procedures": rng.integers(1, 100, n),
        "num_procedures": rng.integers(0, 6, n),
        "num_medications": rng.integers(1, 40, n),
        "number_outpatient": rng.poisson(0.3, n),
        "number_emergency": rng.poisson(0.2, n),
        "number_inpatient": inpatient,
        "diag_1": rng.choice(["428", "250.83", "V57", "786", "?", "820", "715"], n),
        "diag_2": rng.choice(["276", "250.01", "E888", "585", "?"], n),
        "diag_3": rng.choice(["401", "250", "414", "?"], n),
        "number_diagnoses": rng.integers(1, 16, n),
        "max_glu_serum": rng.choice(["None", ">200", ">300", "Norm"], n),
        "A1Cresult": rng.choice(["None", ">7", ">8", "Norm"], n),
        "change": rng.choice(["Ch", "No"], n),
        "diabetesMed": rng.choice(["Yes", "No"], n),
        "readmitted": np.where(readmit, "<30", rng.choice([">30", "NO"], n)),
    })
    for m in MEDICATIONS:
        df[m] = rng.choice(["No", "Steady", "Up", "Down"], n, p=[0.85, 0.1, 0.03, 0.02])
    # Mimic read_csv(na_values=["?"]).
    return df.replace("?", np.nan)


@pytest.fixture(scope="session")
def raw_brfss() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    n = 6000
    bmi = rng.normal(28, 6, n).clip(12, 80).round()
    high_bp = rng.random(n) < 0.4
    age = rng.integers(1, 14, n)
    logit = -4 + 0.08 * (bmi - 28) + 1.0 * high_bp + 0.2 * age
    diabetes = rng.random(n) < 1 / (1 + np.exp(-logit))
    heart = rng.random(n) < 1 / (1 + np.exp(-(-5 + 0.25 * age + 0.8 * diabetes)))
    b = lambda p: (rng.random(n) < p).astype(float)  # noqa: E731
    return pd.DataFrame({
        "ID": np.arange(n), "Diabetes_binary": diabetes.astype(float), "HighBP": high_bp.astype(float),
        "HighChol": b(0.4), "CholCheck": b(0.95), "BMI": bmi, "Smoker": b(0.45), "Stroke": b(0.04),
        "HeartDiseaseorAttack": heart.astype(float), "PhysActivity": b(0.75), "Fruits": b(0.6),
        "Veggies": b(0.8), "HvyAlcoholConsump": b(0.05), "AnyHealthcare": b(0.95), "NoDocbcCost": b(0.08),
        "GenHlth": rng.integers(1, 6, n).astype(float), "MentHlth": rng.integers(0, 31, n).astype(float),
        "PhysHlth": rng.integers(0, 31, n).astype(float), "DiffWalk": b(0.17), "Sex": b(0.44),
        "Age": age.astype(float), "Education": rng.integers(1, 7, n).astype(float),
        "Income": rng.integers(1, 9, n).astype(float),
    })
