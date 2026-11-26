import numpy as np
import pytest

from healthml.tasks import get_task
from healthml.tasks.readmission import age_bracket_to_years, icd9_group, icd10_group
from healthml.train import split


@pytest.mark.parametrize("code,group", [
    ("250.83", "diabetes"), ("428", "circulatory"), ("785", "circulatory"), ("786", "respiratory"),
    ("V57", "other"), ("E888", "other"), ("820", "injury"), ("715", "musculoskeletal"),
    ("185", "neoplasms"), (np.nan, "missing"), ("?", "missing"),
])
def test_icd9_group(code, group):
    assert icd9_group(code) == group


@pytest.mark.parametrize("code,group", [
    ("E11.9", "diabetes"), ("I50.9", "circulatory"), ("J44.1", "respiratory"), ("K21.0", "digestive"),
    ("S72.001A", "injury"), ("N18.3", "genitourinary"), ("C50.9", "neoplasms"), ("Z00.0", "other"), (None, "missing"),
])
def test_icd10_group_matches_training_chapters(code, group):
    assert icd10_group(code) == group


def test_age_bracket():
    assert age_bracket_to_years("[70-80)") == 75


def test_readmission_features(raw_readmission):
    task = get_task("readmission_30d")
    data = task._build(raw_readmission)
    assert list(data.X.columns) == task.features
    assert "race" not in data.X.columns and "race" in data.subgroups.columns
    # Dead / hospice encounters and invalid sex rows are removed.
    assert len(data.X) < len(raw_readmission)
    assert set(data.X["sex"]) <= {"male", "female"}
    assert set(data.y) <= {0, 1}
    # prior_encounters counts only earlier admissions of the same patient.
    first = data.X.groupby(data.groups)["prior_encounters"].min()
    assert (first == 0).all()


def test_split_has_no_patient_leakage(raw_readmission):
    data = get_task("readmission_30d")._build(raw_readmission)
    tr, va, te = split(data)
    g = data.groups.to_numpy()
    assert not (set(g[tr]) & set(g[te])) and not (set(g[tr]) & set(g[va])) and not (set(g[va]) & set(g[te]))
    assert len(tr) + len(va) + len(te) == len(g)


@pytest.mark.parametrize("name,excluded_target", [("diabetes_risk", "diabetes"), ("cvd_risk", "heart_disease")])
def test_brfss_tasks_exclude_target_and_ses(raw_brfss, name, excluded_target):
    task = get_task(name)
    data = task._build(raw_brfss)
    cols = set(data.X.columns)
    assert excluded_target not in cols
    assert not cols & {"Income", "Education", "AnyHealthcare", "NoDocbcCost"}
    assert data.X["age_years"].between(18, 85).all()
