from datetime import datetime, timedelta, timezone

from conftest import signup


def by_model(results):
    return {r["model"]: r for r in results}


def admission(days_since_discharge=3, los=6, **extra):
    end = datetime.now(timezone.utc) - timedelta(days=days_since_discharge)
    body = {
        "type": "inpatient", "started_at": (end - timedelta(days=los)).isoformat(), "ended_at": end.isoformat(),
        "reason": "Breathlessness", "admission_type": "emergency", "admission_source": "emergency_room",
        "discharge_disposition": "facility", "procedure_count": 1,
        "conditions": [{"icd10_code": "I50.9", "description": "Heart failure", "is_primary": True},
                       {"icd10_code": "E11.9", "description": "Type 2 diabetes"},
                       {"icd10_code": "N18.3", "description": "CKD stage 3", "category": "encounter"}],
        "observations": [{"code": "hba1c", "value": 8.6}, {"code": "glucose_random", "value": 320},
                         {"code": "creatinine", "value": 1.8}, {"code": "bp_systolic", "value": 150}],
        "medications": [{"name": "Insulin glargine", "dose": "10 units", "action": "started"},
                        {"name": "Metformin", "dose": "500 mg", "action": "continued"},
                        {"name": "Furosemide", "dose": "40 mg"}],
    }
    body.update(extra)
    return body


def test_readmission_scored_after_discharge(granted, doctor):
    pid = granted.patient_id
    assert by_model(doctor.get(f"/patients/{pid}/risk").json())["readmission_30d"]["status"] == "not_applicable"

    # Two earlier stays in the past year make this a high-utiliser.
    for d in (200, 90):
        doctor.post(f"/patients/{pid}/encounters", json=admission(days_since_discharge=d, los=4))
    r = doctor.post(f"/patients/{pid}/encounters", json=admission())
    assert r.status_code == 201, r.text

    risk = by_model(doctor.get(f"/patients/{pid}/risk").json())
    ra = risk["readmission_30d"]
    assert ra["status"] == "scored", ra
    assert 0 < ra["score"] < 1 and ra["band"] in {"low", "moderate", "high"}
    assert ra["encounter_id"] == r.json()["id"]
    labels = {f["label"]: f for f in ra["factors"]}
    assert labels["Inpatient stays in past year"]["display_value"] == "2"
    assert labels["Inpatient stays in past year"]["direction"] == "increases"

    # Diabetes is recorded, so diabetes screening doesn't apply.
    assert risk["diabetes_risk"]["status"] == "not_applicable"
    # Scores were snapshotted automatically after each encounter.
    hist = doctor.get(f"/patients/{pid}/risk/readmission_30d/history").json()
    assert len(hist) >= 1
    assert doctor.get(f"/patients/{pid}/risk/unknown/history").status_code == 404


def test_old_discharge_not_scored(granted, doctor):
    pid = granted.patient_id
    doctor.post(f"/patients/{pid}/encounters", json=admission(days_since_discharge=60))
    ra = by_model(doctor.get(f"/patients/{pid}/risk").json())["readmission_30d"]
    assert ra["status"] == "not_applicable" and "60 days ago" in ra["reason"]


def test_chronic_models_need_questionnaire(client, doctor):
    p = signup(client, "chronic@test.pht", dob="1968-03-10", sex="male")
    pid = p.patient_id
    p.post(f"/patients/{pid}/access", json={"clinician_id": doctor.id})
    doctor.post(f"/patients/{pid}/encounters", json={
        "type": "outpatient", "started_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "conditions": [{"icd10_code": "I10", "description": "Hypertension"}],
        "observations": [{"code": "bmi", "value": 31.5}, {"code": "bp_systolic", "value": 148},
                         {"code": "cholesterol_total", "value": 250}],
    })
    before = by_model(p.get(f"/patients/{pid}/risk").json())
    assert before["diabetes_risk"]["status"] == "insufficient_data"
    assert "Self-rated general health (1 excellent – 5 poor)" in before["diabetes_risk"]["missing_inputs"]

    r = p.post(f"/patients/{pid}/lifestyle", json={
        "smoker": True, "phys_activity": False, "fruits_daily": False, "veggies_daily": True, "heavy_alcohol": False,
        "general_health": 4, "poor_mental_health_days": 2, "poor_physical_health_days": 10,
        "difficulty_walking": False})
    assert r.status_code == 201
    after = by_model(p.get(f"/patients/{pid}/risk").json())
    for m in ("diabetes_risk", "cvd_risk"):
        assert after[m]["status"] == "scored", after[m]
        assert after[m]["completeness"] == 1.0
        assert all(f["display_value"] != "not recorded" for f in after[m]["factors"])
    factors = {f["label"]: f for f in after["diabetes_risk"]["factors"]}
    assert factors.get("High blood pressure", {}).get("display_value") in (None, "yes")


def test_analytics_scopes_and_monitoring(granted, doctor, other_doctor, admin):
    pid = granted.patient_id
    doctor.post(f"/patients/{pid}/encounters", json=admission(days_since_discharge=45))
    # Admitted again 20 days after that discharge -> one observed 30-day readmission.
    doctor.post(f"/patients/{pid}/encounters", json=admission(days_since_discharge=22, los=3))

    a = admin.get("/analytics/overview").json()
    assert a["scope"] == "population" and a["totals"]["patients"] == 1 and a["totals"]["inpatient_stays"] == 2
    assert any(row["readmitted_30d"] for row in a["readmissions_by_month"])  # 2nd admission within 30 days
    assert a["top_conditions"][0]["icd10_code"] == "I50.9"

    assert doctor.get("/analytics/overview").json()["scope"] == "my_patients"
    assert other_doctor.get("/analytics/overview").json()["totals"]["patients"] == 0
    assert granted.get("/analytics/overview").status_code == 403

    assert isinstance(doctor.get("/analytics/worklist", params={"min_band": "moderate"}).json(), list)
    assert admin.get("/analytics/worklist").status_code == 403

    mon = admin.get("/analytics/models").json()
    assert {m["model"] for m in mon} == {"readmission_30d", "diabetes_risk", "cvd_risk"}
    assert doctor.get("/analytics/models").status_code == 403

    reg = doctor.get("/risk/models").json()
    assert all(0.5 < m["metrics"]["roc_auc"] < 1 for m in reg)


def test_psi():
    from app.routers.analytics import psi

    ref = [i / 100 for i in range(101)]
    same = [i / 1000 + 0.0005 for i in range(1000)]
    shifted = [0.95 + i / 100000 for i in range(1000)]
    assert psi(ref, same) < 0.01
    assert psi(ref, shifted) > 0.25
    assert psi(ref, [0.5] * 5) is None


def test_diabetes_screening_respects_recent_hba1c(client, doctor):
    p = signup(client, "screen@test.pht", dob="1975-01-01", sex="female")
    pid = p.patient_id
    p.post(f"/patients/{pid}/access", json={"clinician_id": doctor.id})
    p.post(f"/patients/{pid}/lifestyle", json={"general_health": 3, "smoker": False, "phys_activity": True,
                                               "fruits_daily": True, "veggies_daily": True, "heavy_alcohol": False,
                                               "poor_mental_health_days": 0, "poor_physical_health_days": 0,
                                               "difficulty_walking": False})
    when = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    doctor.post(f"/patients/{pid}/encounters", json={
        "type": "outpatient", "started_at": when,
        "observations": [{"code": "bmi", "value": 29}, {"code": "bp_systolic", "value": 128},
                         {"code": "cholesterol_total", "value": 190}]})
    assert by_model(p.get(f"/patients/{pid}/risk").json())["diabetes_risk"]["status"] == "scored"

    doctor.post(f"/patients/{pid}/observations", json={"code": "hba1c", "value": 5.2, "observed_at": when})
    r = by_model(p.get(f"/patients/{pid}/risk").json())["diabetes_risk"]
    assert r["status"] == "not_applicable" and "up to date" in r["reason"]

    doctor.post(f"/patients/{pid}/observations", json={"code": "hba1c", "value": 6.0})
    r = by_model(p.get(f"/patients/{pid}/risk").json())["diabetes_risk"]
    assert r["status"] == "not_applicable" and "prediabetes range" in r["reason"]
