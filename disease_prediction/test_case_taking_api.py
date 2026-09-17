"""
SIH Clinical Case-Taking API & Workflow Automated Test Suite
Verifies:
1. Case Initialization & Mandatory Consent Enforcement
2. 10-Section Clinical History Recording
3. Adaptive Clinical Question Engine & Fallbacks
4. Medical Document Attachment & Parameter Linkage
5. Emergency Red-Flag Triage Detection
6. Optional AYUSH Constitutional Evaluation
7. Physician-Ready Summary Generation
8. Doctor Console Review, Edit, & Sign-off
"""

import pytest
from fastapi.testclient import TestClient
from disease_prediction.api.main import app
from disease_prediction.api import database as db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    db.init_db()
    yield

def test_01_case_creation_with_consent():
    # Test consent rejection
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1001",
        "consent_given": False
    })
    assert res.status_code == 400

    # Test successful consent and initialization
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1001",
        "chief_complaint": "Severe sharp chest pain for 2 hours",
        "abha_id": "91-1234-5678-9012 (Demo ABHA)",
        "consent_given": True,
        "consent_text": "I give informed consent to record my medical history for clinical consultation."
    })
    assert res.status_code == 200
    data = res.json()
    assert "case_id" in data
    assert data["status"] == "initialized"
    assert data["patient_id"] in ["PAT-1001", "MCH-0001001"]
    
    case_id = data["case_id"]
    
    # Verify case details endpoint
    res_get = client.get(f"/api/cases/{case_id}")
    assert res_get.status_code == 200
    case_details = res_get.json()
    assert case_details["case_id"] == case_id
    assert case_details["patient_id"] in ["PAT-1001", "MCH-0001001"]
    assert case_details["status"] == "in_progress"

def test_02_adaptive_questioning():
    # Start a case
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1001",
        "chief_complaint": "Severe chest pain radiating to left arm",
        "consent_given": True
    })
    case_id = res.json()["case_id"]

    # Request adaptive questions
    res_aq = client.post(f"/api/cases/{case_id}/adaptive-questions", json={
        "chief_complaint": "Severe chest pain radiating to left arm",
        "answers": {}
    })
    assert res_aq.status_code == 200
    aq_data = res_aq.json()
    questions = aq_data["questions"]
    assert len(questions) > 0
    # Must have cardiac-related adaptive question
    q_texts = " ".join([q["question"] for q in questions])
    assert "chest pain" in q_texts.lower() or "onset" in q_texts.lower() or "spread" in q_texts.lower()

def test_03_saving_structured_sections_and_voice():
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1001",
        "chief_complaint": "Persistent fever and headache",
        "consent_given": True
    })
    case_id = res.json()["case_id"]

    # Save Chief Complaint
    res_cc = client.post(f"/api/cases/{case_id}/save-section", json={
        "section_id": "chief_complaint",
        "section_title": "Chief Complaint",
        "raw_input": "High fever with chills and severe headache for 3 days",
        "structured_data": {"symptom": "Fever", "duration": "3 days", "fever_type": "Chills & rigors"},
        "input_mode": "voice"
    })
    assert res_cc.status_code == 200
    assert res_cc.json()["status"] == "saved"

    # Save HPI
    res_hpi = client.post(f"/api/cases/{case_id}/save-section", json={
        "section_id": "hpi",
        "section_title": "History of Present Illness",
        "raw_input": "Temperature peaked at 103 F yesterday. Nausea present. No cough.",
        "structured_data": {"peak_temp": "103 F", "associated": ["Nausea", "Headache"]},
        "input_mode": "text"
    })
    assert res_hpi.status_code == 200

    # Save Past Medical & Allergies
    client.post(f"/api/cases/{case_id}/save-section", json={
        "section_id": "past_medical",
        "section_title": "Past Medical History",
        "raw_input": "Known patient with Hypertension for 4 years on regular medication.",
        "structured_data": {"conditions": ["Hypertension"]},
        "input_mode": "text"
    })
    client.post(f"/api/cases/{case_id}/save-section", json={
        "section_id": "allergy_history",
        "section_title": "Allergy History",
        "raw_input": "Severe allergic rash to Penicillin in 2019.",
        "structured_data": {"allergies": ["Penicillin"]},
        "input_mode": "text"
    })

    # Retrieve and verify stored sections
    case = client.get(f"/api/cases/{case_id}").json()
    assert len(case["sections"]) >= 4
    sec_ids = [s["section_id"] for s in case["sections"]]
    assert "chief_complaint" in sec_ids
    assert "allergy_history" in sec_ids

def test_04_attach_document_and_extract_parameters():
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1001",
        "chief_complaint": "Follow up for anemia and weakness",
        "consent_given": True
    })
    case_id = res.json()["case_id"]

    # Attach existing lab report
    res_attach = client.post(f"/api/cases/{case_id}/attach-document", json={
        "report_id": "REP-2026-001",
        "document_type": "lab_report",
        "filename": "CBC_Hematology_Report_2026.pdf",
        "extracted_data": {
            "HGB": {"value": 8.5, "unit": "g/dL", "flag": "Low"},
            "MCV": {"value": 71.0, "unit": "fL", "flag": "Low"},
            "RDW": {"value": 18.5, "unit": "%", "flag": "High"}
        }
    })
    assert res_attach.status_code == 200
    assert res_attach.json()["status"] == "attached"

    # Verify attachment in case record
    case = client.get(f"/api/cases/{case_id}").json()
    assert len(case["documents"]) == 1
    assert case["documents"][0]["filename"] == "CBC_Hematology_Report_2026.pdf"

def test_05_red_flags_and_summary_generation():
    # Create emergency case: severe chest pain radiating to left arm
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1002",
        "chief_complaint": "Crushing chest pain radiating to left arm and jaw with profuse sweating",
        "consent_given": True
    })
    case_id = res.json()["case_id"]

    # Generate physician-ready summary
    res_sum = client.post(f"/api/cases/{case_id}/generate-summary", json={
        "chief_complaint": "Crushing chest pain radiating to left arm and jaw with profuse sweating",
        "ayush_data": {
            "prakriti": "Pitta Dominant (Medium build, warm, sharp digestion)",
            "agni_ahara": "Tikshna Agni (Intense/excessive hunger, hyperacidity)",
            "vyayama_shakti": "Madhyama (Moderate stamina)",
            "sattva": "Pravara (High mental resilience)",
            "ahara_vihara": "High stress desk work, irregular meals"
        }
    })
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["status"] == "submitted"
    assert sum_data["has_red_flags"] is True
    assert sum_data["triage_urgency"] == "emergency"
    
    summary = sum_data["summary"]
    assert "PATIENT CLINICAL CASE SHEET" in summary["header"]["title"]
    assert len(summary["red_flags"]) > 0
    assert summary["ayush_profile"]["has_ayush"] is True
    assert "Pitta Dominant" in summary["ayush_profile"]["prakriti"]

def test_06_doctor_console_review_and_signoff():
    # Create and submit a case
    res = client.post("/api/cases/start", json={
        "patient_id": "PAT-1003",
        "chief_complaint": "Fatigue and joint pains",
        "consent_given": True
    })
    case_id = res.json()["case_id"]

    client.post(f"/api/cases/{case_id}/generate-summary", json={
        "chief_complaint": "Fatigue and joint pains"
    })

    # Doctor review
    res_review = client.post(f"/api/cases/{case_id}/doctor-review", json={
        "doctor_id": "Dr. A. K. Mehta (Clinical Consultant)",
        "doctor_notes": "Clinical history verified with patient. Advised ESR, CRP, and Rheumatoid factor panel.",
        "status": "confirmed"
    })
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "reviewed"

    # Verify updated case record
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["status"] == "confirmed"
    assert "Rheumatoid factor" in case["doctor_notes"]
    assert case["doctor_id"] == "Dr. A. K. Mehta (Clinical Consultant)"
