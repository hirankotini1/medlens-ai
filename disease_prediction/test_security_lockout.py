import pytest
from fastapi.testclient import TestClient
from api.main import app, login_limiter

client = TestClient(app)

def test_unauthenticated_routes_rejected():
    # Reports list without auth
    res = client.get("/api/reports")
    assert res.status_code == 401
    assert "token required" in res.json()["detail"].lower()

    # Patients list without auth
    res_pat = client.get("/api/patients")
    assert res_pat.status_code == 401

def test_admin_login_brute_force_lockout():
    test_user = "brute_attacker_admin"
    headers = {"x-forwarded-for": "10.0.0.1"}

    # 4 invalid attempts should return 401
    for i in range(4):
        res = client.post("/api/auth/login", json={"username": test_user, "password": "wrongpassword"}, headers=headers)
        assert res.status_code == 401

    # 5th failed attempt triggers lockout
    res_5 = client.post("/api/auth/login", json={"username": test_user, "password": "wrongpassword"}, headers=headers)
    assert res_5.status_code == 429
    assert "Retry-After" in res_5.headers

    # 6th attempt should immediately return 429
    res_6 = client.post("/api/auth/login", json={"username": test_user, "password": "wrongpassword"}, headers=headers)
    assert res_6.status_code == 429
    assert "Retry-After" in res_6.headers

def test_patient_login_brute_force_lockout():
    test_pid = "PAT-FAKE-PATIENT"
    headers = {"x-forwarded-for": "10.0.0.2"}

    for i in range(4):
        res = client.post("/api/patient/login", json={"patient_id": test_pid, "access_pin": "WRONGPIN"}, headers=headers)
        assert res.status_code == 401

    # 5th failed attempt triggers lockout
    res_5 = client.post("/api/patient/login", json={"patient_id": test_pid, "access_pin": "WRONGPIN"}, headers=headers)
    assert res_5.status_code == 429
    assert "Retry-After" in res_5.headers

    # 6th attempt returns 429
    res_6 = client.post("/api/patient/login", json={"patient_id": test_pid, "access_pin": "WRONGPIN"}, headers=headers)
    assert res_6.status_code == 429

def test_ml_prediction_uncertainty_and_calibration():
    payload = {
        "Age": 32,
        "Sex": "Female",
        "HGB": 8.0,
        "RBC": 3.5,
        "PCV": 26.0,
        "MCV": 70.0,
        "MCH": 21.0,
        "MCHC": 28.0,
        "RDW": 18.0,
        "TLC": 6.5,
        "PLT /mm3": 210.0
    }
    res = client.post("/predict/anemia", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "uncertainty_range" in data
    assert len(data["uncertainty_range"]) == 2
    assert "calibration_note" in data
    assert data["disease"] == "Anemia"
