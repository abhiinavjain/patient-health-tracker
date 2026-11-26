"""30-day hospital readmission risk.

Dataset: UCI "Diabetes 130-US hospitals for years 1999-2008" (~101k inpatient encounters, ~71k patients).
Target:  readmitted within 30 days of discharge.

Design decisions (documented in the model card):
* Encounters ending in death or hospice are removed — readmission is not a possible outcome.
* Race is NOT a model input. It is kept only for subgroup performance reporting.
* `weight` (97% missing) and `payer_code` (insurance, not clinical) are dropped.
* ICD-9 diagnosis codes are grouped into clinical chapters; an ICD-10 helper maps app-side codes to
  the same groups so the live app can score its own encounters.
* Splits are grouped by patient so no person appears in both train and test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..download import csv_path
from .base import Task, TaskData

MEDICATIONS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride", "acetohexamide",
    "glipizide", "glyburide", "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose", "miglitol",
    "troglitazone", "tolazamide", "examide", "citoglipton", "insulin", "glyburide-metformin",
    "glipizide-metformin", "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone",
]

# IDs_mapping.csv: dispositions where a 30-day readmission cannot happen.
EXPIRED_OR_HOSPICE = {11, 13, 14, 19, 20, 21}

ADMISSION_TYPE = {1: "emergency", 7: "emergency", 2: "urgent", 3: "elective"}
DISCHARGE_TO = {
    1: "home",
    6: "home_health", 8: "home_health",
    **{k: "facility" for k in (2, 3, 4, 5, 15, 22, 23, 24, 27, 28, 29, 30)},
    7: "left_ama",
}
ADMISSION_SOURCE = {
    7: "emergency_room",
    **{k: "referral" for k in (1, 2, 3)},
    **{k: "transfer" for k in (4, 5, 6, 10, 18, 22, 25, 26)},
}
TOP_SPECIALTIES = [
    "InternalMedicine", "Emergency/Trauma", "Family/GeneralPractice", "Cardiology", "Surgery-General",
    "Nephrology", "Orthopedics", "Orthopedics-Reconstructive", "Radiologist", "Pulmonology",
]


def icd9_group(code) -> str:
    """Map an ICD-9 code string to a clinical chapter (Strack et al. 2014 grouping)."""
    if code is None or (isinstance(code, float) and np.isnan(code)) or code in ("", "?"):
        return "missing"
    s = str(code).strip()
    if s[:1] in ("V", "E"):
        return "other"
    try:
        v = float(s)
    except ValueError:
        return "other"
    if 250 <= v < 251:
        return "diabetes"
    if 390 <= v <= 459 or int(v) == 785:
        return "circulatory"
    if 460 <= v <= 519 or int(v) == 786:
        return "respiratory"
    if 520 <= v <= 579 or int(v) == 787:
        return "digestive"
    if 800 <= v <= 999:
        return "injury"
    if 710 <= v <= 739:
        return "musculoskeletal"
    if 580 <= v <= 629 or int(v) == 788:
        return "genitourinary"
    if 140 <= v <= 239:
        return "neoplasms"
    return "other"


def icd10_group(code: str | None) -> str:
    """Map an ICD-10 code (as stored by the v2 app) to the same chapters used in training."""
    if not code:
        return "missing"
    s = code.strip().upper().replace(".", "")
    letter, rest = s[:1], s[1:3]
    num = int(rest) if rest.isdigit() else -1
    if letter == "E" and 8 <= num <= 13:
        return "diabetes"
    if letter == "I" or s.startswith("R00") or s.startswith("R01"):
        return "circulatory"
    if letter == "J" or s.startswith("R06"):
        return "respiratory"
    if letter == "K" or s.startswith("R1"):
        return "digestive"
    if letter in ("S", "T"):
        return "injury"
    if letter == "M":
        return "musculoskeletal"
    if letter == "N" or s.startswith("R3"):
        return "genitourinary"
    if letter == "C" or (letter == "D" and 0 <= num <= 49):
        return "neoplasms"
    return "other"


def age_bracket_to_years(bracket: str) -> float:
    """'[70-80)' -> 75.0"""
    lo, hi = bracket.strip("[)").split("-")
    return (float(lo) + float(hi)) / 2


def age_band(age_years: pd.Series) -> pd.Series:
    return pd.cut(age_years, [0, 45, 65, 200], right=False, labels=["<45", "45-64", "65+"]).astype(str)


class ReadmissionTask(Task):
    def __init__(self) -> None:
        super().__init__(
            name="readmission_30d",
            title="30-day hospital readmission risk",
            target_description="Patient is readmitted to hospital within 30 days of this discharge.",
            dataset="uci_diabetes_130",
            numeric=[
                "age_years", "time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications",
                "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses",
                "n_diabetes_meds", "n_med_changes", "med_change", "on_diabetes_med", "prior_encounters",
            ],
            categorical=[
                "sex", "admission_type", "discharge_to", "admission_source", "specialty",
                "diag_1_group", "diag_2_group", "diag_3_group", "a1c_result", "max_glucose", "insulin",
            ],
            labels={
                "age_years": "Age",
                "time_in_hospital": "Days in hospital",
                "num_lab_procedures": "Lab tests this stay",
                "num_procedures": "Procedures this stay",
                "num_medications": "Distinct medications this stay",
                "number_outpatient": "Outpatient visits in past year",
                "number_emergency": "Emergency visits in past year",
                "number_inpatient": "Inpatient stays in past year",
                "number_diagnoses": "Number of recorded diagnoses",
                "n_diabetes_meds": "Diabetes medications in use",
                "n_med_changes": "Diabetes medication dose changes",
                "med_change": "Any diabetes medication changed",
                "on_diabetes_med": "On diabetes medication",
                "prior_encounters": "Earlier admissions on record",
                "sex": "Sex",
                "admission_type": "Admission type",
                "discharge_to": "Discharged to",
                "admission_source": "Admitted from",
                "specialty": "Admitting specialty",
                "diag_1_group": "Primary diagnosis",
                "diag_2_group": "Secondary diagnosis",
                "diag_3_group": "Additional diagnosis",
                "a1c_result": "HbA1c result",
                "max_glucose": "Max serum glucose",
                "insulin": "Insulin",
            },
            value_text={
                "med_change": {0: "no", 1: "yes"},
                "on_diabetes_med": {0: "no", 1: "yes"},
            },
            intended_use=(
                "Rank adult inpatients with diabetes at discharge by their likelihood of 30-day readmission, "
                "so a care team with limited capacity can prioritise follow-up calls, medication reconciliation "
                "and early outpatient appointments. Decision support only — not for denying care."
            ),
            limitations=[
                "Training data is 1999–2008 US hospital encounters of diabetic patients; "
                "practice patterns and coding have changed and the population is not Indian or global.",
                "Readmissions to a different hospital are not observed in the source data (label noise).",
                "ICD-9 → ICD-10 mapping for live use is chapter-level only.",
                "Discrimination on this dataset is modest in published work (ROC-AUC ≈ 0.65–0.70); "
                "use as a prioritisation aid, not a diagnostic.",
            ],
        )

    def load(self) -> TaskData:
        path = csv_path(self.dataset)
        raw = pd.read_csv(path, keep_default_na=False, na_values=["?", ""], low_memory=False)
        return self._build(raw, str(path))

    def _build(self, raw: pd.DataFrame, source: str = "") -> TaskData:
        df = raw.copy()
        df = df[~df["discharge_disposition_id"].isin(EXPIRED_OR_HOSPICE)]
        df = df[df["gender"].isin(["Male", "Female"])]
        # encounter_id increases with time; use it to count each patient's earlier admissions.
        df = df.sort_values("encounter_id").reset_index(drop=True)

        meds = df[MEDICATIONS].fillna("No")
        out = pd.DataFrame(index=df.index)
        out["age_years"] = df["age"].map(age_bracket_to_years)
        for c in ["time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications",
                  "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses"]:
            out[c] = df[c].astype(float)
        out["n_diabetes_meds"] = (meds != "No").sum(axis=1).astype(float)
        out["n_med_changes"] = meds.isin(["Up", "Down"]).sum(axis=1).astype(float)
        out["med_change"] = (df["change"] == "Ch").astype(float)
        out["on_diabetes_med"] = (df["diabetesMed"] == "Yes").astype(float)
        out["prior_encounters"] = df.groupby("patient_nbr").cumcount().astype(float)

        out["sex"] = df["gender"].str.lower()
        out["admission_type"] = df["admission_type_id"].map(ADMISSION_TYPE).fillna("other")
        out["discharge_to"] = df["discharge_disposition_id"].map(DISCHARGE_TO).fillna("other")
        out["admission_source"] = df["admission_source_id"].map(ADMISSION_SOURCE).fillna("other")
        spec = df["medical_specialty"]
        out["specialty"] = np.where(spec.isna(), "missing", np.where(spec.isin(TOP_SPECIALTIES), spec, "other"))
        for i in (1, 2, 3):
            out[f"diag_{i}_group"] = df[f"diag_{i}"].map(icd9_group)
        # Older UCI exports use the string "None" for "not measured"; newer ones leave it blank.
        out["a1c_result"] = df["A1Cresult"].fillna("None").replace({"None": "not_measured"})
        out["max_glucose"] = df["max_glu_serum"].fillna("None").replace({"None": "not_measured"})
        out["insulin"] = df["insulin"].fillna("No").str.lower()

        y = (df["readmitted"] == "<30").astype(int)
        subgroups = pd.DataFrame({
            "race": df["race"].fillna("Unknown"),
            "sex": out["sex"],
            "age_band": age_band(out["age_years"]),
        })
        X = out[self.features]
        return TaskData(X=X, y=y, groups=df["patient_nbr"], subgroups=subgroups, source_csv=source)
