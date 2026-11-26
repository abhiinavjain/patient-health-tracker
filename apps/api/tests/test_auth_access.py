from conftest import PASSWORD, signup


def test_signup_login_refresh(client, patient):
    me = patient.get("/auth/me").json()
    assert me["role"] == "patient" and me["patient_id"] == patient.patient_id

    bad = client.post("/api/v1/auth/login", data={"username": patient.email, "password": "wrong-password"})
    assert bad.status_code == 401
    unknown = client.post("/api/v1/auth/login", data={"username": "nobody@test.pht", "password": PASSWORD})
    assert unknown.status_code == 401

    tokens = client.post("/api/v1/auth/login", data={"username": patient.email, "password": PASSWORD}).json()
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    # An access token must not work as a refresh token, and vice versa.
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401


def test_signup_validation(client, patient):
    dup = client.post("/api/v1/auth/signup", json={"email": patient.email.upper(), "password": PASSWORD,
                                                   "full_name": "X Y", "date_of_birth": "1990-01-01", "sex": "male"})
    assert dup.status_code == 409
    short = client.post("/api/v1/auth/signup", json={"email": "a@test.pht", "password": "short",
                                                     "full_name": "X Y", "date_of_birth": "1990-01-01", "sex": "male"})
    assert short.status_code == 422


def test_unauthenticated_requests_rejected(client, patient):
    assert client.get(f"/api/v1/patients/{patient.patient_id}").status_code == 401
    assert client.get("/api/v1/patients", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_clinician_needs_grant_and_revoke_removes_access(patient, doctor):
    pid = patient.patient_id
    assert doctor.get(f"/patients/{pid}").status_code == 403
    assert doctor.get("/patients").json() == []

    g = patient.post(f"/patients/{pid}/access", json={"clinician_id": doctor.id}).json()
    assert doctor.get(f"/patients/{pid}").status_code == 200
    assert [p["id"] for p in doctor.get("/patients").json()] == [pid]

    assert patient.delete(f"/patients/{pid}/access/{g['id']}").status_code == 204
    assert doctor.get(f"/patients/{pid}").status_code == 403
    assert patient.get(f"/patients/{pid}/access").json() == []
    assert len(patient.get(f"/patients/{pid}/access", params={"include_revoked": True}).json()) == 1


def test_patients_are_isolated(client, patient):
    other = signup(client, "other@test.pht")
    assert other.get(f"/patients/{patient.patient_id}").status_code == 403
    assert [p["id"] for p in other.get("/patients").json()] == [other.patient_id]


def test_admin_cannot_open_charts(admin, patient):
    assert admin.get("/patients").status_code == 403
    assert admin.get(f"/patients/{patient.patient_id}").status_code == 403


def test_only_patient_manages_access(granted, doctor, other_doctor):
    pid = granted.patient_id
    assert doctor.post(f"/patients/{pid}/access", json={"clinician_id": other_doctor.id}).status_code == 403
    assert doctor.get(f"/patients/{pid}/audit").status_code == 403


def test_clinician_registers_walk_in_and_gets_access(doctor, other_doctor):
    r = doctor.post("/patients", json={"full_name": "Walk In", "date_of_birth": "1970-02-03", "sex": "male",
                                       "blood_group": "O+"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["mrn"].startswith("PHT")
    assert doctor.get(f"/patients/{pid}").status_code == 200
    assert other_doctor.get(f"/patients/{pid}").status_code == 403


def test_admin_user_management(admin, doctor):
    r = admin.post("/admin/users", json={"email": "new@test.pht", "password": PASSWORD, "full_name": "Dr New",
                                         "role": "clinician", "specialty": "Cardiology"})
    assert r.status_code == 201
    assert doctor.post("/admin/users", json={"email": "x@test.pht", "password": PASSWORD, "full_name": "X Y",
                                             "role": "admin"}).status_code == 403
    off = admin.patch(f"/admin/users/{doctor.id}", json={"is_active": False})
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert doctor.get("/auth/me").status_code == 401  # deactivated users lose access immediately
    assert admin.patch(f"/admin/users/{admin.id}", json={"is_active": False}).status_code == 400
