"""
Unit & Integration Tests for SIM-Based SMS Patient Alert Gateway in MedLens AI
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure disease_prediction is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.main import app, generate_signed_token
from api.sms_gateway import normalize_phone, build_sms_text
import api.database as db

client = TestClient(app)

ADMIN_GATEWAY_TOKEN = "medlens-sms-gateway-secret-2026"
ADMIN_USER_TOKEN = generate_signed_token({"role": "admin", "username": "admin_doctor"})
ADMIN_AUTH_HEADERS = {"Authorization": f"Bearer {ADMIN_USER_TOKEN}"}


# ==============================================================================
# 1. Phone Normalization Tests
# ==============================================================================

def test_normalize_phone_standard_10_digit():
    assert normalize_phone("9876543210") == "+919876543210"

def test_normalize_phone_with_leading_zero():
    assert normalize_phone("09876543210") == "+919876543210"

def test_normalize_phone_with_plus_91():
    assert normalize_phone("+919876543210") == "+919876543210"

def test_normalize_phone_with_spaces_and_dashes():
    assert normalize_phone("+91 98765-43210") == "+919876543210"
    assert normalize_phone(" 98765 43210 ") == "+919876543210"

def test_normalize_phone_invalid():
    assert normalize_phone("12345") is None
    assert normalize_phone("abcdefghij") is None
    assert normalize_phone("1234567890") is None  # Does not start with 6, 7, 8, 9
    assert normalize_phone("") is None
    assert normalize_phone(None) is None


# ==============================================================================
# 2. SMS Template Engine & Safety Tests
# ==============================================================================

def test_build_sms_text_medication():
    text = build_sms_text(
        patient_name="Rajesh Kumar",
        message_type="medication_reminder",
        custom_message="Take with warm water",
        medication_name="Metformin",
        dosage="500mg",
        dose_unit="tablet",
        administration_time="After Breakfast, 8:00 AM",
        due_date="2026-09-20"
    )
    assert "Rajesh Kumar" in text
    assert "Metformin" in text
    assert "500mg" in text
    assert "After Breakfast, 8:00 AM" in text
    assert len(text) <= 320

def test_build_sms_text_appointment():
    text = build_sms_text(
        patient_name="Priya Sharma",
        message_type="appointment_reminder",
        custom_message="Report 15 mins prior to Medicover Vizag",
        due_date="2026-09-22"
    )
    assert "Priya Sharma" in text
    assert "2026-09-22" in text
    assert len(text) <= 320

def test_build_sms_text_truncation():
    # Verify strict length guarantee for GSM SMS safety
    long_msg = "A" * 500
    text = build_sms_text(
        patient_name="Ananya Rao",
        message_type="daily_care",
        custom_message=long_msg
    )
    assert len(text) <= 320


# ==============================================================================
# 3. Database Layer Tests
# ==============================================================================

def test_db_device_registration_and_lookup():
    dev = db.register_gateway_device(
        device_id="dev-samsung-s23",
        device_name="Test Samsung Galaxy S23",
        raw_token="test-secret-token-xyz-123"
    )
    assert dev is not None
    assert dev["device_name"] == "Test Samsung Galaxy S23"
    assert dev["status"] == "active"

    # Lookup by token
    found = db.get_gateway_device_by_token("test-secret-token-xyz-123")
    assert found is not None
    assert found["device_id"] == "dev-samsung-s23"

    # Touch device
    db.touch_gateway_device("dev-samsung-s23")
    refreshed = db.get_gateway_device_by_token("test-secret-token-xyz-123")
    assert refreshed["last_seen_at"] is not None

def test_db_sms_queue_claim_and_status_flow():
    sms = db.create_sms_outbox_entry(
        patient_id="PAT-1001",
        phone_number="+919876543210",
        message="MedLens AI test SMS message content",
        message_type="test"
    )
    assert sms["id"] is not None
    assert sms["status"] == "queued"

    sms_id = sms["id"]

    # Claim message
    claimed = db.claim_sms_message(sms_id, device_id="dev-samsung-s23")
    assert claimed is not None
    assert claimed["status"] == "processing"

    # Double claim should return None (atomic claim protection)
    double_claim = db.claim_sms_message(sms_id, device_id="dev-samsung-s23")
    assert double_claim is None

    # Mark as sent
    updated = db.update_sms_status(sms_id, device_id="dev-samsung-s23", status="sent")
    assert updated is not None
    assert updated["status"] == "sent"
    assert updated["sent_at"] is not None


# ==============================================================================
# 4. API Endpoints Integration Tests
# ==============================================================================

def test_gateway_device_registration_api():
    res = client.post(
        "/api/sms-gateway/register",
        json={
            "device_id": "redmi-note-12-station",
            "device_name": "Nurse Station Redmi Note 12",
            "admin_token": ADMIN_GATEWAY_TOKEN
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "registered"
    assert "gateway_token" in data
    assert data["device_id"] == "redmi-note-12-station"

    token = data["gateway_token"]

    # Gateway status with device token
    status_res = client.get("/api/sms-gateway/status", headers={"X-Gateway-Token": token})
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["device_name"] == "Nurse Station Redmi Note 12"
    assert status_data["gateway_status"] == "online"

def test_gateway_admin_test_sms_and_claim_flow():
    # 1. Register a test phone
    reg = client.post(
        "/api/sms-gateway/register",
        json={
            "device_id": "test-dispatch-phone-01",
            "device_name": "Test Dispatch Phone",
            "admin_token": ADMIN_GATEWAY_TOKEN
        }
    )
    device_token = reg.json()["gateway_token"]

    # 2. Queue a test SMS as admin
    test_res = client.post(
        "/api/sms-gateway/test",
        headers={"X-Admin-Token": ADMIN_GATEWAY_TOKEN},
        json={"phone_number": "+919876543210", "message": "Test SMS from pytest"}
    )
    assert test_res.status_code == 200
    sms_data = test_res.json()
    sms_id = sms_data["sms_id"]
    assert sms_data["status"] == "queued"

    # 3. Android Gateway polls queue
    queue_res = client.get("/api/sms-gateway/queue", headers={"X-Gateway-Token": device_token})
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["messages"]
    assert any(item["id"] == sms_id for item in queue_items)

    # 4. Android Gateway claims the message
    claim_res = client.post(f"/api/sms-gateway/{sms_id}/claim", headers={"X-Gateway-Token": device_token})
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "claimed"
    assert claim_res.json()["phone_number"] == "+919876543210"

    # 5. Android Gateway reports success
    status_res = client.post(
        f"/api/sms-gateway/{sms_id}/status",
        headers={"X-Gateway-Token": device_token},
        json={"status": "sent"}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "updated"
    assert status_res.json()["new_status"] == "sent"

def test_care_reminder_with_sms_integration():
    # Make sure PAT-1001 exists with phone number
    db.init_db()
    conn = db.get_db_connection()
    conn.execute("UPDATE patients SET contact = '+919876543210' WHERE patient_id = 'PAT-1001'")
    conn.commit()
    conn.close()

    # Create reminder with send_sms=True
    res = client.post(
        "/api/reminders",
        headers=ADMIN_AUTH_HEADERS,
        json={
            "patient_id": "PAT-1001",
            "reminder_type": "medication_reminder",
            "title": "Evening Antibiotic",
            "message": "Take with water after dinner",
            "send_sms": True,
            "medication_name": "Amoxicillin",
            "dosage": "500mg",
            "dose_unit": "capsule",
            "administration_time": "9:00 PM",
            "due_date": "2026-09-25",
            "frequency": "daily",
            "sent_by": "Dr. Medicover"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["sms_queued"] is True
    assert data["sms_id"] is not None
    assert data["sms_status"] == "queued"

    # Verify patient reminders endpoint returns sms_status
    rem_res = client.get("/api/reminders/PAT-1001", headers=ADMIN_AUTH_HEADERS)
    assert rem_res.status_code == 200
    reminders = rem_res.json()["reminders"]
    matching = [r for r in reminders if r["id"] == data["reminder"]["id"]]
    assert len(matching) == 1
    assert matching[0]["sms_status"] in ["queued", "processing", "sent"]

def test_backward_compatibility_care_reminder():
    # Calling /api/reminders without any SMS fields should succeed normally
    res = client.post(
        "/api/reminders",
        headers=ADMIN_AUTH_HEADERS,
        json={
            "patient_id": "PAT-1001",
            "reminder_type": "daily_care",
            "title": "Classic Legacy Reminder",
            "message": "Stay hydrated throughout the day"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "reminder" in data
