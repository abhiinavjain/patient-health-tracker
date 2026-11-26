"""Chronic-disease risk from routinely collectable health indicators.

Dataset: CDC BRFSS 2015 "Diabetes Health Indicators" (253,680 survey respondents, UCI id 891).
Two tasks share one feature pipeline:
  * diabetes_risk  — target: told they have prediabetes or diabetes
  * cvd_risk       — target: coronary heart disease or myocardial infarction

Only inputs the app can realistically collect from vitals, the problem list and a short lifestyle
questionnaire are used. Income, education and insurance/cost-access variables are intentionally
excluded: they are not clinical, and using them would encode socioeconomic status into a health score.
"""

from __future__ import annotations

import pandas as pd

from ..download import csv_path
from .base import Task, TaskData

# BRFSS _AGEG5YR codes 1..13 -> midpoint age in years (13 = 80+).
AGE_CODE_TO_YEARS = {1: 21, 2: 27, 3: 32, 4: 37, 5: 42, 6: 47, 7: 52, 8: 57, 9: 62, 10: 67, 11: 72, 12: 77, 13: 82}

RENAME = {
    "Diabetes_binary": "diabetes",
    "HighBP": "high_bp",
    "HighChol": "high_chol",
    "CholCheck": "chol_check_5y",
    "BMI": "bmi",
    "Smoker": "smoker",
    "Stroke": "stroke",
    "HeartDiseaseorAttack": "heart_disease",
    "PhysActivity": "phys_activity",
    "Fruits": "fruits_daily",
    "Veggies": "veggies_daily",
    "HvyAlcoholConsump": "heavy_alcohol",
    "GenHlth": "general_health",
    "MentHlth": "poor_mental_health_days",
    "PhysHlth": "poor_physical_health_days",
    "DiffWalk": "difficulty_walking",
    "Sex": "sex_male",
}

SHARED_FEATURES = [
    "age_years", "sex_male", "bmi", "high_bp", "high_chol", "chol_check_5y", "smoker", "stroke",
    "phys_activity", "fruits_daily", "veggies_daily", "heavy_alcohol", "general_health",
    "poor_mental_health_days", "poor_physical_health_days", "difficulty_walking",
]

LABELS = {
    "age_years": "Age",
    "sex_male": "Sex (male)",
    "bmi": "BMI",
    "high_bp": "High blood pressure",
    "high_chol": "High cholesterol",
    "chol_check_5y": "Cholesterol checked in past 5 years",
    "smoker": "Smoked 100+ cigarettes in lifetime",
    "stroke": "History of stroke",
    "heart_disease": "Coronary heart disease / heart attack",
    "diabetes": "Prediabetes or diabetes",
    "phys_activity": "Physically active in past 30 days",
    "fruits_daily": "Eats fruit daily",
    "veggies_daily": "Eats vegetables daily",
    "heavy_alcohol": "Heavy alcohol use",
    "general_health": "Self-rated general health (1 excellent – 5 poor)",
    "poor_mental_health_days": "Poor mental-health days (past 30)",
    "poor_physical_health_days": "Poor physical-health days (past 30)",
    "difficulty_walking": "Difficulty walking or climbing stairs",
}

YES_NO = {0: "no", 1: "yes"}
BINARY_FEATURES = [
    "sex_male", "high_bp", "high_chol", "chol_check_5y", "smoker", "stroke", "heart_disease", "diabetes",
    "phys_activity", "fruits_daily", "veggies_daily", "heavy_alcohol", "difficulty_walking",
]

COMMON_LIMITATIONS = [
    "Self-reported survey data (BRFSS 2015, United States): diagnoses are 'ever told by a doctor', "
    "not lab-confirmed, and the population differs from Indian/global patients.",
    "Cross-sectional: the model estimates current prevalence-style risk, not a validated 10-year incidence "
    "(it is not a replacement for clinical scores such as ADA risk test, QRISK or WHO CVD charts).",
    "Age is coarsened to 5-year bands in the source data.",
]


def load_brfss() -> tuple[pd.DataFrame, str]:
    path = csv_path("cdc_brfss_2015")
    raw = pd.read_csv(path)
    return raw, str(path)


def build_brfss(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=RENAME)
    df["age_years"] = df["Age"].map(AGE_CODE_TO_YEARS).astype(float)
    keep = SHARED_FEATURES + ["diabetes", "heart_disease"]
    return df[keep].astype(float)


def _subgroups(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "sex": df["sex_male"].map({1.0: "male", 0.0: "female"}),
        "age_band": pd.cut(df["age_years"], [0, 45, 65, 200], right=False, labels=["<45", "45-64", "65+"]).astype(str),
    })


class _BRFSSTask(Task):
    target_col: str = ""

    def load(self) -> TaskData:
        raw, source = load_brfss()
        return self._build(raw, source)

    def _build(self, raw: pd.DataFrame, source: str = "") -> TaskData:
        df = build_brfss(raw)
        return TaskData(
            X=df[self.features],
            y=df[self.target_col].astype(int),
            groups=None,
            subgroups=_subgroups(df),
            source_csv=source,
        )


class DiabetesRiskTask(_BRFSSTask):
    target_col = "diabetes"

    def __init__(self) -> None:
        super().__init__(
            name="diabetes_risk",
            title="Prediabetes / diabetes risk",
            target_description="Respondent reports a doctor ever told them they have prediabetes or diabetes.",
            dataset="cdc_brfss_2015",
            numeric=SHARED_FEATURES + ["heart_disease"],
            categorical=[],
            labels=LABELS,
            value_text={f: YES_NO for f in BINARY_FEATURES},
            intended_use=(
                "Flag adults who may have undiagnosed prediabetes/diabetes so they can be offered an HbA1c "
                "or fasting-glucose test. Screening prompt only — never a diagnosis."
            ),
            limitations=COMMON_LIMITATIONS,
        )


class CVDRiskTask(_BRFSSTask):
    target_col = "heart_disease"

    def __init__(self) -> None:
        super().__init__(
            name="cvd_risk",
            title="Coronary heart disease risk",
            target_description="Respondent reports coronary heart disease or a previous myocardial infarction.",
            dataset="cdc_brfss_2015",
            numeric=SHARED_FEATURES + ["diabetes"],
            categorical=[],
            labels=LABELS,
            value_text={f: YES_NO for f in BINARY_FEATURES},
            intended_use=(
                "Highlight patients whose risk-factor profile resembles people with coronary heart disease, "
                "to prompt a clinician to review BP, lipids and lifestyle. Decision support only."
            ),
            limitations=COMMON_LIMITATIONS,
        )
