"""Controlled vocabularies used by the record and by the feature builders."""

from __future__ import annotations

# code -> (label, unit, LOINC)
OBSERVATIONS: dict[str, tuple[str, str, str]] = {
    "bp_systolic": ("Systolic blood pressure", "mmHg", "8480-6"),
    "bp_diastolic": ("Diastolic blood pressure", "mmHg", "8462-4"),
    "heart_rate": ("Heart rate", "bpm", "8867-4"),
    "spo2": ("Oxygen saturation", "%", "59408-5"),
    "temperature": ("Body temperature", "°C", "8310-5"),
    "weight": ("Body weight", "kg", "29463-7"),
    "height": ("Body height", "cm", "8302-2"),
    "bmi": ("Body mass index", "kg/m2", "39156-5"),
    "hba1c": ("HbA1c", "%", "4548-4"),
    "glucose_fasting": ("Fasting glucose", "mg/dL", "1558-6"),
    "glucose_random": ("Random glucose", "mg/dL", "2339-0"),
    "glucose_postprandial": ("Post-meal glucose (2 h)", "mg/dL", "1521-4"),
    "cholesterol_total": ("Total cholesterol", "mg/dL", "2093-3"),
    "ldl": ("LDL cholesterol", "mg/dL", "18262-6"),
    "hdl": ("HDL cholesterol", "mg/dL", "2085-9"),
    "triglycerides": ("Triglycerides", "mg/dL", "2571-8"),
    "creatinine": ("Creatinine", "mg/dL", "2160-0"),
    "egfr": ("eGFR", "mL/min/1.73m2", "33914-3"),
    "hemoglobin": ("Hemoglobin", "g/dL", "718-7"),
}

LAB_CODES = {"hba1c", "glucose_fasting", "glucose_random", "glucose_postprandial", "cholesterol_total", "ldl", "hdl", "triglycerides",
             "creatinine", "egfr", "hemoglobin"}

# Generic names of glucose-lowering drugs (incl. those in the readmission training data).
DIABETES_DRUGS = {
    "metformin", "insulin", "glimepiride", "glipizide", "glyburide", "gliclazide", "pioglitazone",
    "rosiglitazone", "sitagliptin", "vildagliptin", "linagliptin", "empagliflozin", "dapagliflozin",
    "canagliflozin", "liraglutide", "semaglutide", "dulaglutide", "acarbose", "repaglinide", "nateglinide",
}

# Clinician specialty -> specialty label used in the readmission training data.
SPECIALTY_MAP = {
    "internal medicine": "InternalMedicine",
    "emergency medicine": "Emergency/Trauma",
    "family medicine": "Family/GeneralPractice",
    "general practice": "Family/GeneralPractice",
    "cardiology": "Cardiology",
    "general surgery": "Surgery-General",
    "nephrology": "Nephrology",
    "orthopedics": "Orthopedics",
    "pulmonology": "Pulmonology",
    "radiology": "Radiologist",
}


def icd_prefix_in(code: str, *prefixes: str) -> bool:
    c = code.upper().replace(".", "")
    return any(c.startswith(p.replace(".", "")) for p in prefixes)
