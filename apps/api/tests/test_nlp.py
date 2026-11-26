from datetime import date, datetime, timedelta, timezone

import pytest

from app.nlp.evaluate import evaluate, load, score_note
from app.nlp.local import LocalExtractor, words_to_numbers
from app.nlp.normalize import dose_key, med_key
from app.nlp.rules import RuleExtractor
from app.nlp.schema import ExtractedCondition, ExtractedMedication, ExtractedObservation, NoteExtraction
from app.nlp.service import build_draft


# ----------------------------------------------------------------------------- normalisation & rules
def test_normalisation():
    assert med_key("Formoterol/Budesonide") == med_key("budesonide-formoterol")
    assert med_key("Glycomet") == med_key("metformin")
    assert dose_key("1 g") == dose_key("1000mg") == "1000 mg"
    assert dose_key("18 U") == "18 units"


def test_rules_negation_aliases_and_units():
    ex = RuleExtractor().extract(
        "62F, HTN. No diabetes. Denies chest pain. Avoid NSAIDs given CKD. SpO2 96% RA.\n"
        "Wt 198 lbs. T 101.8 F. FBS 7.8 mmol/L.\n"
        "Amlong increased from 5 to 10 mg OD. Stop pantoprazole. Started Telma 40 mg OD.\n"
        "Review in 2 weeks.")
    cats = {c.icd10_code[:3] for c in ex.conditions}
    assert cats == {"I10", "N18"}  # diabetes negated, CKD kept, 'RA' after SpO2 is room air
    meds = {m.name: m for m in ex.medications}
    assert "ibuprofen" not in meds and "diclofenac" not in meds
    assert meds["amlodipine"].action == "dose_increased" and meds["amlodipine"].dose == "10 mg"
    assert meds["pantoprazole"].action == "stopped"
    assert meds["telmisartan"].action == "started" and meds["telmisartan"].frequency == "once_daily"
    obs = {o.code: o.value for o in ex.observations}
    assert obs["weight"] == pytest.approx(89.8, abs=0.1)
    assert obs["temperature"] == pytest.approx(38.8, abs=0.1)
    assert obs["glucose_fasting"] == pytest.approx(140.4, abs=0.1)
    assert ex.follow_up_days == 14


def test_rule_baseline_regression_on_dev():
    res = evaluate(RuleExtractor().extract, load("dev"))
    assert res["entities"]["all"]["f1"] >= 0.95


def test_scorer_counts_alternatives_and_optional_items():
    gold = {"conditions": [["I25", "I21"]], "conditions_optional": ["E66"], "medications": [
        {"name": "budesonide-formoterol", "action": "started", "dose": "200/6 mcg", "frequency": "twice_daily"}],
        "medications_optional": [], "observations": [["bp_systolic", 140]], "observations_optional": [["bp_systolic", 120]],
        "follow_up_days": 14}
    pred = NoteExtraction(
        conditions=[ExtractedCondition(icd10_code="I21.4", description="NSTEMI", evidence="x"),
                    ExtractedCondition(icd10_code="E66.9", description="Obesity", evidence="x")],
        medications=[ExtractedMedication(name="formoterol/budesonide", action="started", dose="200/6 mcg",
                                         frequency="twice_daily", evidence="x")],
        observations=[ExtractedObservation(code="bp_systolic", value=141, evidence="x"),
                      ExtractedObservation(code="bp_systolic", value=120, evidence="x")],
        follow_up_days=15)
    s = score_note(pred, gold)
    assert (s.conditions.tp, s.conditions.fp, s.conditions.fn) == (1, 0, 0)
    assert (s.medications.tp, s.medications.fp) == (1, 0) and s.dose.acc == 1.0
    assert (s.observations.tp, s.observations.fp) == (1, 0)
    assert s.follow_up.correct == 1


# ----------------------------------------------------------------------------- local extractor (v2)
def test_words_to_numbers():
    assert words_to_numbers("BP one hundred and forty over ninety") == "BP 140/90"
    assert words_to_numbers("BP one sixty over a hundred") == "BP 160/100"
    assert words_to_numbers("one puff BD") == "1 puff BD"


def test_local_handles_messy_text():
    ex = LocalExtractor(action_model=False).extract(
        "k/c/o hypertenshun. On metfromin. Telma 40 le rahi hai. Telma 80 kar diya.\n"
        "BP was one forty over ninety. O2 sat 93%. ECG: ST depression V4-V6.\n"
        "Started isoniazid 300 mg OD. Transfused 1 unit PRBC. Vitamin B12 also low at 150.\n"
        "FU 3/12.")
    cats = {c.icd10_code[:3] for c in ex.conditions}
    assert "I10" in cats and "F32" not in cats            # misspelling fixed; ECG "ST depression" ignored
    meds = {m.name: m for m in ex.medications}
    assert meds["metformin"].action == "continued"
    assert meds["telmisartan"].action == "dose_increased" and meds["telmisartan"].dose == "80 mg"
    assert meds["isoniazid"].action == "started"
    assert "transfused" not in meds and "vitamin b12" not in meds
    obs = {o.code: o.value for o in ex.observations}
    assert obs["bp_systolic"] == 140 and obs["bp_diastolic"] == 90 and obs["spo2"] == 93
    assert ex.follow_up_days == 90
    # evidence quotes the original note, not the normalised text
    assert any("hypertenshun" in c.evidence for c in ex.conditions)


def test_local_beats_v1_on_stress_and_keeps_precision():
    rows = load("stress")
    v1 = evaluate(RuleExtractor().extract, rows)["entities"]["all"]
    v2 = evaluate(LocalExtractor().extract, rows)["entities"]["all"]
    assert v2["recall"] > v1["recall"] + 0.2 and v2["precision"] >= 0.95


def test_holdout_split_is_untouched():
    import hashlib
    from app.nlp.evaluate import EVAL_PATH
    lines = [l for l in EVAL_PATH.read_text().splitlines() if '"split": "holdout"' in l]
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    assert digest == (EVAL_PATH.parent / ".holdout.sha256").read_text().split()[0]


# ----------------------------------------------------------------------------- validation
def test_build_draft_drops_ungrounded_implausible_and_invalid():
    note = "BP 150/90. Started amlodipine 5 mg OD. Known HTN."
    ex = NoteExtraction(
        conditions=[ExtractedCondition(icd10_code="I10", description="Hypertension", evidence="Known HTN"),
                    ExtractedCondition(icd10_code="E11.9", description="T2DM", evidence="known diabetic"),  # not in note
                    ExtractedCondition(icd10_code="HTN", description="bad code", evidence="Known HTN")],
        medications=[ExtractedMedication(name="amlodipine", action="started", dose="5 mg", frequency="once_daily",
                                         evidence="Started amlodipine 5 mg OD")],
        observations=[ExtractedObservation(code="bp_systolic", value=150, evidence="BP 150/90"),
                      ExtractedObservation(code="spo2", value=960, evidence="BP 150/90")],
        follow_up_days=14)
    draft, review, warnings = build_draft(note, ex, None, date(2026, 1, 1))
    assert [c.icd10_code for c in draft.conditions] == ["I10"]
    assert [o.code for o in draft.observations] == ["bp_systolic"]
    assert draft.medications[0].frequency == "once daily"
    assert draft.follow_up_date == date(2026, 1, 15)
    reasons = {r.label: r.reason for r in review if r.status == "dropped"}
    assert any("not found" in r for r in reasons.values())
    assert any("ICD-10" in r for r in reasons.values())
    assert any("plausible" in r for r in reasons.values())
    assert warnings


# ----------------------------------------------------------------------------- endpoint: extract -> review -> save
def test_extract_reconciles_and_draft_can_be_saved(granted, doctor):
    pid = granted.patient_id
    start = datetime.now(timezone.utc) - timedelta(days=60)
    doctor.post(f"/patients/{pid}/encounters", json={
        "type": "outpatient", "started_at": start.isoformat(),
        "conditions": [{"icd10_code": "I10", "description": "Hypertension"}],
        "medications": [{"name": "Metformin", "dose": "500 mg", "frequency": "twice daily"},
                        {"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily"}]})

    note = ("Known HTN, T2DM. BP 152/94, HR 80. HbA1c 8.6%.\n"
            "Amlodipine increased to 10 mg OD. Stop metformin due to GI upset. Start sitagliptin 100 mg OD.\n"
            "Review in 4 weeks.")
    r = doctor.post(f"/patients/{pid}/notes/extract", json={"note": note})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["extractor"].startswith("local")
    by_label = {i["label"]: i for i in res["review"]}
    assert any(i["status"] == "already_recorded" and i["label"].startswith("I10") for i in res["review"])
    draft = res["draft"]
    assert [c["icd10_code"][:3] for c in draft["conditions"]] == ["E11"]
    assert {m["name"]: m["action"] for m in draft["medications"]} == {"amlodipine": "dose_increased",
                                                                       "sitagliptin": "started"}
    assert len(draft["stop_medication_ids"]) == 2  # metformin stopped + old amlodipine dose replaced
    assert draft["follow_up_date"] is not None
    assert by_label  # every item carries a label for the review UI

    # Patients cannot run extraction; the endpoint never writes clinical data by itself.
    assert granted.post(f"/patients/{pid}/notes/extract", json={"note": note}).status_code == 403
    assert len(granted.get(f"/patients/{pid}/encounters").json()) == 1

    # Clinician approves the draft -> saved through the normal encounter endpoint.
    save = doctor.post(f"/patients/{pid}/encounters", json={
        "type": "outpatient", "started_at": datetime.now(timezone.utc).isoformat(), "notes": note, **draft})
    assert save.status_code == 201, save.text
    meds = {m["name"].lower(): m for m in granted.get(f"/patients/{pid}/summary").json()["active_medications"]}
    assert set(meds) == {"amlodipine", "sitagliptin"} and meds["amlodipine"]["dose"] == "10 mg"
    log = granted.get(f"/patients/{pid}/audit").json()
    assert any(e["action"] == "extract" for e in log)


def test_field_report_post_meal_sugar():
    """Reported from real use: misspelled post-meal sugar was missed entirely."""
    ex = LocalExtractor(action_model=False).extract(
        "Suger after lunch 200, increased thrist, frequent urination, advice hb1ac test  reccomend to cardiologist")
    assert [(o.code, o.value) for o in ex.observations] == [("glucose_postprandial", 200.0)]
    assert not ex.conditions and not ex.medications  # symptoms aren't diagnoses; an ordered test isn't a result


@pytest.mark.parametrize("note,expected", [
    ("PPBS 248 mg/dl, FBS 162", {("glucose_postprandial", 248.0), ("glucose_fasting", 162.0)}),
    ("sugar 210 after food. Fasting sugar 140", {("glucose_postprandial", 210.0), ("glucose_fasting", 140.0)}),
    ("Blood sugar 7.8 mmol/L", {("glucose_random", 140.4)}),
    ("GRBS 312 in ER", {("glucose_random", 312.0)}),
    ("sugar 5 days back was high", set()),
    ("hb1ac 8.9%", {("hba1c", 8.9)}),
])
def test_glucose_variants(note, expected):
    ex = LocalExtractor(action_model=False).extract(note)
    assert {(o.code, round(o.value, 1)) for o in ex.observations} == expected
