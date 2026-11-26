from datetime import datetime, timedelta, timezone


def visit(days_ago=10, **extra):
    start = datetime.now(timezone.utc) - timedelta(days=days_ago)
    body = {
        "type": "outpatient", "started_at": start.isoformat(), "reason": "Follow-up",
        "conditions": [{"icd10_code": "i10", "description": "Essential hypertension", "is_primary": True}],
        "observations": [{"code": "bp_systolic", "value": 152}, {"code": "bp_diastolic", "value": 96},
                         {"code": "weight", "value": 82.5}],
        "medications": [{"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily"}],
    }
    body.update(extra)
    return body


def test_consultation_updates_history(granted, doctor):
    pid = granted.patient_id
    r = doctor.post(f"/patients/{pid}/encounters", json=visit())
    assert r.status_code == 201, r.text
    enc = r.json()
    assert enc["clinician"]["id"] == doctor.id
    assert enc["conditions"][0]["icd10_code"] == "I10"  # normalised
    assert {o["code"] for o in enc["observations"]} == {"bp_systolic", "bp_diastolic", "weight"}

    s = granted.get(f"/patients/{pid}/summary").json()
    assert [c["description"] for c in s["active_conditions"]] == ["Essential hypertension"]
    assert [m["name"] for m in s["active_medications"]] == ["Amlodipine"]
    assert {o["code"]: o["value"] for o in s["latest_observations"]}["bp_systolic"] == 152
    assert s["encounter_count"] == 1 and s["last_encounter"]["diagnoses"] == ["I10 Essential hypertension"]

    # Second visit: BP improved, amlodipine stopped and replaced.
    aml = s["active_medications"][0]["id"]
    r2 = doctor.post(f"/patients/{pid}/encounters", json=visit(
        days_ago=1, conditions=[], observations=[{"code": "bp_systolic", "value": 134}],
        medications=[{"name": "Telmisartan", "dose": "40 mg"}], stop_medication_ids=[aml]))
    assert r2.status_code == 201, r2.text
    s = granted.get(f"/patients/{pid}/summary").json()
    assert [m["name"] for m in s["active_medications"]] == ["Telmisartan"]

    series = granted.get(f"/patients/{pid}/observations/series", params={"codes": "bp_systolic"}).json()[0]
    assert [p["value"] for p in series["points"]] == [152, 134] and series["unit"] == "mmHg"

    tl = granted.get(f"/patients/{pid}/timeline").json()
    assert tl[0]["kind"] in {"encounter", "medication"}
    ats = [e["at"] for e in tl]
    assert ats == sorted(ats, reverse=True)
    assert any(e["title"] == "Stopped: Amlodipine" for e in tl)


def test_encounter_validation(granted, doctor):
    pid = granted.patient_id
    bad_code = visit(observations=[{"code": "blood_magic", "value": 1}])
    assert doctor.post(f"/patients/{pid}/encounters", json=bad_code).status_code == 422
    bad_unit = visit(observations=[{"code": "weight", "value": 180, "unit": "lb"}])
    assert doctor.post(f"/patients/{pid}/encounters", json=bad_unit).status_code == 422
    two_primary = visit(conditions=[{"icd10_code": "I10", "description": "HTN", "is_primary": True},
                                    {"icd10_code": "E11.9", "description": "T2DM", "is_primary": True}])
    assert doctor.post(f"/patients/{pid}/encounters", json=two_primary).status_code == 422
    bad_icd = visit(conditions=[{"icd10_code": "hello", "description": "nope"}])
    assert doctor.post(f"/patients/{pid}/encounters", json=bad_icd).status_code == 422
    reversed_times = visit(ended_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat())
    assert doctor.post(f"/patients/{pid}/encounters", json=reversed_times).status_code == 422


def test_patient_permissions_on_record(granted):
    pid = granted.patient_id
    assert granted.post(f"/patients/{pid}/encounters", json=visit()).status_code == 403
    home_bp = granted.post(f"/patients/{pid}/observations", json={"code": "bp_systolic", "value": 128})
    assert home_bp.status_code == 201 and home_bp.json()["source"] == "patient"
    assert granted.post(f"/patients/{pid}/observations", json={"code": "hba1c", "value": 5.0}).status_code == 403
    assert granted.post(f"/patients/{pid}/allergies", json={"substance": "Penicillin", "severity": "severe"}).status_code == 201
    assert granted.patch(f"/patients/{pid}", json={"phone": "+91 99999 00000"}).json()["phone"] == "+91 99999 00000"


def test_condition_resolution(granted, doctor):
    pid = granted.patient_id
    enc = doctor.post(f"/patients/{pid}/encounters", json=visit()).json()
    cid = enc["conditions"][0]["id"]
    r = doctor.patch(f"/patients/{pid}/conditions/{cid}", json={"status": "resolved"})
    assert r.status_code == 200 and r.json()["resolved_date"] is not None
    assert granted.get(f"/patients/{pid}/conditions", params={"status": "active"}).json() == []


def test_audit_trail_visible_to_patient(granted, doctor, admin):
    pid = granted.patient_id
    doctor.get(f"/patients/{pid}/summary")
    log = granted.get(f"/patients/{pid}/audit").json()
    assert any(e["action"] == "view" and e["actor_role"] == "clinician" and e["entity"] == "summary" for e in log)
    assert any(e["action"] == "grant" for e in log)
    admin_log = admin.get("/admin/audit", params={"patient_id": pid}).json()
    assert len(admin_log) == len(log)


def test_appointments(granted, doctor, other_doctor, patient):
    pid = granted.patient_id
    soon = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert granted.post(f"/patients/{pid}/appointments", json={"clinician_id": doctor.id, "starts_at": past}).status_code == 422

    # Booking with a new clinician grants them access (audited).
    assert other_doctor.get(f"/patients/{pid}").status_code == 403
    r = granted.post(f"/patients/{pid}/appointments", json={"clinician_id": other_doctor.id, "starts_at": soon,
                                                           "reason": "Chest pain review"})
    assert r.status_code == 201
    appt = r.json()
    assert other_doctor.get(f"/patients/{pid}").status_code == 200
    assert [a["id"] for a in other_doctor.get("/appointments").json()] == [appt["id"]]
    assert [a["id"] for a in granted.get("/appointments").json()] == [appt["id"]]

    assert granted.patch(f"/appointments/{appt['id']}", json={"starts_at": soon}).status_code == 403
    assert granted.patch(f"/appointments/{appt['id']}", json={"status": "cancelled"}).json()["status"] == "cancelled"
    # A clinician with access to the patient can update it too.
    assert doctor.patch(f"/appointments/{appt['id']}", json={"status": "completed"}).status_code == 200
