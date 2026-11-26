"""End-to-end: train on synthetic data, reload artifacts, score app-style records."""

import json

import pytest

from healthml.predict import RiskModel
from healthml.tasks import get_task
from healthml.train import run


@pytest.fixture(scope="module")
def trained(tmp_path_factory, raw_readmission):
    out = tmp_path_factory.mktemp("artifacts")
    data = get_task("readmission_30d")._build(raw_readmission)
    run("readmission_30d", n_trials=3, out_root=out, data=data, make_report=True)
    return out


def test_artifacts_written(trained):
    d = trained / "readmission_30d"
    for f in ["model.txt", "metadata.json", "MODEL_CARD.md", "subgroups.csv", "figures/roc_pr.png"]:
        assert (d / f).exists(), f
    md = json.loads((d / "metadata.json").read_text())
    assert md["split"]["grouped_by_patient"] is True
    assert 0 < md["risk_bands"]["moderate"] < md["risk_bands"]["high"] < 1


def test_predict_handles_partial_and_unknown_inputs(trained):
    model = RiskModel.load("readmission_30d", trained)
    out = model.predict([
        {"age_years": 75, "number_inpatient": 4, "time_in_hospital": 9, "discharge_to": "facility",
         "diag_1_group": "circulatory", "sex": "female"},
        {"age_years": 40, "number_inpatient": 0, "sex": "martian", "specialty": "never-seen"},
    ])
    assert len(out) == 2
    for r in out:
        assert 0 < r["score"] < 1
        assert r["band"] in {"low", "moderate", "high"}
        assert 0 <= r["percentile"] <= 100
        assert all(f["direction"] in {"increases", "decreases"} for f in r["factors"])
    # Strong synthetic signal: more prior inpatient stays -> higher risk.
    assert out[0]["score"] > out[1]["score"]
    assert "num_medications" in out[0]["missing_features"]
    # Missing / unseen inputs are imputed and never presented as explanations.
    for r in out:
        assert not {f["feature"] for f in r["factors"]} & set(r["missing_features"])
    assert "sex" in out[1]["missing_features"] and "specialty" in out[1]["missing_features"]
    assert 0 < out[0]["completeness"] < 1
