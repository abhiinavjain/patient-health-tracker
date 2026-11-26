"""Paths and global settings for the ML pipeline."""

from __future__ import annotations

import os
from pathlib import Path

ML_ROOT = Path(os.environ.get("HEALTHML_ROOT", Path(__file__).resolve().parents[2]))
DATA_RAW = ML_ROOT / "data" / "raw"
ARTIFACTS = Path(os.environ.get("HEALTHML_ARTIFACTS", ML_ROOT / "artifacts"))

SEED = 42

# Public, de-identified datasets (UCI Machine Learning Repository, CC BY 4.0).
DATASETS = {
    "uci_diabetes_130": {
        "url": "https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip",
        "filename": "diabetes_130.zip",
        "csv": "diabetic_data.csv",
        "citation": "Strack et al. (2014), 'Impact of HbA1c Measurement on Hospital Readmission Rates', "
        "BioMed Research International. UCI ML Repository id 296.",
    },
    "cdc_brfss_2015": {
        "url": "https://archive.ics.uci.edu/static/public/891/data.csv",
        "filename": "cdc_diabetes_health_indicators.csv",
        "csv": "cdc_diabetes_health_indicators.csv",
        "citation": "CDC Behavioral Risk Factor Surveillance System 2015, 'CDC Diabetes Health Indicators'. "
        "UCI ML Repository id 891.",
    },
}
