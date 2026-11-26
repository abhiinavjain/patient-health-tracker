from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.alerts import assess


def obs(code, value, hours_ago=0):
    return SimpleNamespace(code=code, value=value, unit="", observed_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago))


@pytest.mark.parametrize("readings,level", [
    ([("bp_systolic", 124), ("heart_rate", 72), ("spo2", 98), ("temperature", 36.8)], "normal"),
    ([("heart_rate", 98)], "watch"),                                  # NEWS2 1
    ([("bp_systolic", 186), ("bp_diastolic", 112)], "urgent"),        # severe hypertension
    ([("bp_systolic", 230), ("bp_diastolic", 135)], "critical"),      # hypertensive crisis
    ([("spo2", 87)], "critical"),
    ([("respiratory_rate", 26), ("heart_rate", 118), ("temperature", 39.4), ("spo2", 94)], "critical"),  # NEWS2 3+2+2+1=8
    ([("glucose_random", 48)], "critical"),
    ([("glucose_postprandial", 320)], "urgent"),
    ([("hemoglobin", 6.5)], "critical"),
    ([("hba1c", 11.6), ("ldl", 190)], "normal"),                      # chronic markers aren't acute emergencies
])
def test_levels(readings, level):
    assert assess([obs(c, v) for c, v in readings]).level == level


def test_news2_score_and_reasons():
    a = assess([obs("respiratory_rate", 26), obs("heart_rate", 118), obs("temperature", 39.4), obs("spo2", 94)])
    assert a.news2 == 8 and a.news2_partial
    assert a.reasons[0].severity in ("critical", "urgent")


def test_old_readings_dont_count():
    # A dangerous value from three days ago, followed by normal readings today, is not a current emergency.
    assert assess([obs("spo2", 85, hours_ago=72), obs("spo2", 97)]).level == "normal"


def visit(observations, days_ago=0):
    return {"type": "outpatient", "started_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
            "observations": observations}


def test_alert_flow_review_then_release(granted, doctor):
    pid = granted.patient_id
    r = doctor.post(f"/patients/{pid}/encounters", json=visit([{"code": "bp_systolic", "value": 232}, {"code": "bp_diastolic", "value": 136}]))
    assert r.status_code == 201
    alert = r.json()["alert"]
    assert alert["level"] == "critical" and alert["reasons"][0]["rule"].startswith("Systolic BP")

    # Patient can't see it before review; clinician's open list has it.
    assert granted.get(f"/patients/{pid}/alerts").json() == []
    assert [a["id"] for a in doctor.get("/alerts").json()] == [alert["id"]]

    # Review without releasing: closes it, still hidden from the patient.
    doctor.post(f"/patients/{pid}/alerts/{alert['id']}/review", json={"release_to_patient": False})
    assert doctor.get("/alerts").json() == [] and granted.get(f"/patients/{pid}/alerts").json() == []

    # A new critical reading, reviewed and released, reaches the patient.
    r = doctor.post(f"/patients/{pid}/encounters", json=visit([{"code": "spo2", "value": 86}]))
    a2 = r.json()["alert"]
    assert granted.post(f"/patients/{pid}/alerts/{a2['id']}/review", json={"release_to_patient": True}).status_code == 403
    rel = doctor.post(f"/patients/{pid}/alerts/{a2['id']}/review", json={"release_to_patient": True, "note": "Called patient"})
    assert rel.json()["released_to_patient"] and rel.json()["reviewer_name"]
    seen = granted.get(f"/patients/{pid}/alerts").json()
    assert [a["id"] for a in seen] == [a2["id"]]
    assert granted.post(f"/patients/{pid}/alerts/{a2['id']}/seen").json()["patient_seen_at"]


def test_normal_visit_raises_no_alert_and_home_reading_does(granted, doctor):
    pid = granted.patient_id
    r = doctor.post(f"/patients/{pid}/encounters", json=visit([{"code": "bp_systolic", "value": 122}]))
    assert r.json()["alert"] is None
    granted.post(f"/patients/{pid}/observations", json={"code": "bp_systolic", "value": 228})
    open_ = doctor.get("/alerts").json()
    assert len(open_) == 1 and open_[0]["source"] == "patient" and open_[0]["patient_name"]
