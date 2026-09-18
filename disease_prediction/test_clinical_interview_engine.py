"""
MEDLENS AI — Clinical Interview Engine (SIH PS 26047)
Comprehensive Automated Test Suite: 45+ Scenarios across English, Hindi, Telugu, Odia.
Covers:
- 17 specialized clinical pathways + generic OPQRST fallback
- Open-ended first question generation in multiple Indic languages
- Red flag detection, triage escalation, emergency interruption, and safe instructions
- Clinical entity extraction (duration, severity, location, medications, allergies)
- Information gap analyzer & dynamic question skipping
- Priority-driven questioning (P0 > P1 > P2 > P3 > P4)
- Patient correction with audit provenance
- Contradiction engine (patient statements vs uploaded documents)
- Chronological timeline synthesis & provenance logger
- Quick Consultation Snapshot, detailed case history, and completeness meter
- Patient privacy filtering (no PIN/PII leakage in patient mode)
- Full REST API endpoint verification
"""

import pytest
from fastapi.testclient import TestClient
from disease_prediction.api.main import app
from disease_prediction.api import clinical_interview as ci
from disease_prediction.api import database as db

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    db.init_db()


# ==============================================================================
# 1. CLINICAL ONTOLOGY & PATHWAYS (17 Specialized + Generic OPQRST)
# ==============================================================================

def test_ontology_contains_17_pathways():
    """Verifies all 17 clinical pathways are defined in the clinical ontology."""
    assert len(ci.CLINICAL_ONTOLOGY) >= 17
    required_pathways = [
        "chest_pain", "fever", "cough", "breathlessness", "abdominal_pain",
        "headache", "vomiting", "diarrhea", "urinary_symptoms", "dizziness",
        "joint_pain", "back_pain", "skin_allergy", "diabetes_metabolic",
        "hypertension_cardio", "throat_symptoms", "weakness_fatigue"
    ]
    for p in required_pathways:
        assert p in ci.CLINICAL_ONTOLOGY, f"Missing clinical pathway: {p}"

def test_pathway_routing_chest_pain():
    p = ci.get_pathway_for_complaint("Severe chest heaviness and pain")
    assert p["domain"] == "chest_pain"

def test_pathway_routing_fever_indic():
    p_hi = ci.get_pathway_for_complaint("मुझे ३ दिन से तेज बुखार है")
    assert p_hi["domain"] == "fever"
    p_te = ci.get_pathway_for_complaint("నాకు తీవ్రమైన జ్వరం వచ్చింది")
    assert p_te["domain"] == "fever"
    p_or = ci.get_pathway_for_complaint("ମୋତେ ୩ ଦିନ ହେଲା ଭୀଷଣ ଜ୍ୱର ହେଉଛି")
    assert p_or["domain"] == "fever"

def test_pathway_routing_cough():
    p = ci.get_pathway_for_complaint("dry persistent cough for two weeks")
    assert p["domain"] == "cough"

def test_pathway_routing_headache():
    p = ci.get_pathway_for_complaint("throbbing headache on right side")
    assert p["domain"] == "headache"

def test_pathway_routing_abdominal_pain():
    p = ci.get_pathway_for_complaint("severe stomach ache after meals")
    assert p["domain"] == "abdominal_pain"

def test_pathway_routing_breathlessness():
    p = ci.get_pathway_for_complaint("shortness of breath when climbing stairs")
    assert p["domain"] == "breathlessness"

def test_pathway_routing_vomiting():
    p = ci.get_pathway_for_complaint("vomiting and nausea since morning")
    assert p["domain"] == "vomiting"

def test_pathway_routing_diarrhoea():
    p = ci.get_pathway_for_complaint("frequent loose motions and diarrhoea")
    assert p["domain"] == "diarrhea"

def test_pathway_routing_urinary():
    p = ci.get_pathway_for_complaint("burning sensation during urination")
    assert p["domain"] == "urinary_symptoms"

def test_pathway_routing_joint_pain():
    p = ci.get_pathway_for_complaint("both knees swollen and aching")
    assert p["domain"] == "joint_pain"

def test_pathway_routing_skin_allergy():
    p = ci.get_pathway_for_complaint("itchy red skin rash with hives")
    assert p["domain"] == "skin_allergy"

def test_pathway_routing_dizziness():
    p = ci.get_pathway_for_complaint("feeling dizzy and spinning room")
    assert p["domain"] == "dizziness"

def test_pathway_routing_back_pain():
    p = ci.get_pathway_for_complaint("lower back pain radiating down leg")
    assert p["domain"] == "back_pain"

def test_pathway_routing_fatigue():
    p = ci.get_pathway_for_complaint("extreme exhaustion and weakness")
    assert p["domain"] == "weakness_fatigue"

def test_pathway_routing_diabetes():
    p = ci.get_pathway_for_complaint("routine diabetic blood sugar check-up")
    assert p["domain"] == "diabetes_metabolic"

def test_pathway_routing_hypertension():
    p = ci.get_pathway_for_complaint("high blood pressure hypertension review")
    assert p["domain"] == "hypertension_cardio"

def test_pathway_routing_throat():
    p = ci.get_pathway_for_complaint("sore throat and pain swallowing")
    assert p["domain"] == "throat_symptoms"

def test_generic_opqrst_fallback():
    """Unmatched complaint falls back to generic OPQRST pathway."""
    p = ci.get_pathway_for_complaint("unusual tingling in left big toe")
    assert p is None
    generic_questions = ci.get_generic_pathway()
    assert len(generic_questions) >= 7


# ==============================================================================
# 2. OPEN-ENDED FIRST QUESTION ACROSS 5 LANGUAGES
# ==============================================================================

def test_open_ended_first_question_english():
    q = ci.ClinicalQuestionEngine.generate_open_ended_first_question("en-IN")
    assert "Please tell me in your own words what is bothering you today." in q["question"]["en-IN"]

def test_open_ended_first_question_hindi():
    q = ci.ClinicalQuestionEngine.generate_open_ended_first_question("hi-IN")
    assert "कृपया अपने शब्दों में बताएं" in q["question"]["hi-IN"]

def test_open_ended_first_question_telugu():
    q = ci.ClinicalQuestionEngine.generate_open_ended_first_question("te-IN")
    assert "దయచేసి మీ మాటల్లో చెప్పండి" in q["question"]["te-IN"]

def test_open_ended_first_question_odia():
    q = ci.ClinicalQuestionEngine.generate_open_ended_first_question("or-IN")
    assert "ଦୟାକରି ଆପଣଙ୍କ ନିଜ ଭାଷାରେ କୁହନ୍ତୁ" in q["question"]["or-IN"]

def test_open_ended_first_question_tamil():
    q = ci.ClinicalQuestionEngine.generate_open_ended_first_question("ta-IN")
    assert "சொந்த வார்த்தைகளில்" in q["question"]["ta-IN"]


# ==============================================================================
# 3. RED-FLAG DETECTION & TRIAGE INTERRUPTION
# ==============================================================================

def test_red_flag_chest_pain_english():
    rf = ci.RedFlagEngine.evaluate("I have severe crushing chest pain radiating to left arm", "en-IN")
    assert rf is not None
    assert rf["urgency"] == "CRITICAL"
    assert "Immediate Attention Required" in rf["instruction"]

def test_red_flag_chest_pain_hindi():
    rf = ci.RedFlagEngine.evaluate("मेरे सीने में दर्द और भारीपन हो रहा है", "hi-IN")
    assert rf is not None
    assert rf["urgency"] == "CRITICAL"

def test_red_flag_breathlessness_telugu():
    rf = ci.RedFlagEngine.evaluate("నాకు తీవ్రమైన ఆయాసం ఊపిరి ఆడట్లేదు", "te-IN")
    assert rf is not None
    assert rf["urgency"] == "CRITICAL"

def test_red_flag_odia_acute():
    rf = ci.RedFlagEngine.evaluate("ମୋର ଛାତି ଯନ୍ତ୍ରଣା ହେଉଛି ଏବଂ ନିଶ୍ୱାସ ନେଇପାରୁନାହିଁ", "or-IN")
    assert rf is not None
    assert rf["urgency"] == "CRITICAL"

def test_red_flag_interruption_formatting():
    rf = ci.RedFlagEngine.evaluate("I am coughing up blood and gasping", "en-IN")
    resp = ci.RedFlagEngine.format_interruption_response(rf, "en-IN")
    assert resp["status"] == "PAUSED_RED_FLAG"
    assert resp["is_emergency"] is True
    assert resp["action_required"] == "SEEK_IMMEDIATE_CARE"


# ==============================================================================
# 4. CLINICAL ENTITY EXTRACTION & CONFIDENCE
# ==============================================================================

def test_extract_duration_english():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("I have had this fever for 3 days", language="en-IN")
    assert "duration" in ext
    assert ext["duration"]["value"] == "3 days"
    assert ext["duration"]["confidence"] >= 0.8

def test_extract_duration_hindi():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("२ हफ्ते से खांसी है", language="hi-IN")
    assert "duration" in ext
    assert "हफ्ते" in ext["duration"]["value"] or "week" in ext["duration"]["value"].lower()

def test_extract_duration_odia():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("ମୋତେ ୫ ଦିନ ହେଲା କଷ୍ଟ ହେଉଛି", language="or-IN")
    assert "duration" in ext
    assert "ଦିନ" in ext["duration"]["value"] or "day" in ext["duration"]["value"].lower()

def test_extract_severity_numeric():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("The pain is about 8 out of 10", language="en-IN")
    assert "severity" in ext
    assert ext["severity"]["value"] == 8

def test_extract_severity_qualitative():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("It is unbearable and extremely severe", language="en-IN")
    assert "severity" in ext
    assert ext["severity"]["value"] >= 7

def test_extract_medications():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("I take Metformin 500mg and Amlodipine daily", language="en-IN")
    assert "medications" in ext
    assert "Metformin" in ext["medications"]["value"]

def test_extract_allergies():
    ext = ci.ClinicalAnswerExtractor.extract_from_text("I have an allergy to Penicillin", language="en-IN")
    assert "allergies" in ext
    assert "Penicillin" in ext["allergies"]["value"]


# ==============================================================================
# 5. INFORMATION GAP ANALYZER & QUESTION PRIORITY ENGINE
# ==============================================================================

def test_information_gap_skips_already_known_duration():
    state = ci.create_initial_patient_state(case_id="TEST-01", patient_id="P-01")
    state = ci.PatientStateManager.set_chief_complaint(state, "Chest pain")
    state = ci.PatientStateManager.update_hpi_parameter(state, "duration", "3 days", source="patient_voice")

    next_q = ci.ClinicalQuestionEngine.select_next_question(state, "en-IN")
    assert next_q is not None
    # Next question must NOT be duration since duration is already known
    assert next_q["parameter"] != "duration"

def test_priority_engine_selects_p1_before_p2():
    state = ci.create_initial_patient_state(case_id="TEST-02", patient_id="P-02")
    state = ci.PatientStateManager.set_chief_complaint(state, "Cough")
    next_q = ci.ClinicalQuestionEngine.select_next_question(state, "en-IN")
    assert next_q is not None
    assert next_q["priority"] in ["P0", "P1"]


# ==============================================================================
# 6. PATIENT CORRECTION & CONTRADICTION ENGINE
# ==============================================================================

def test_patient_correction_rectifies_duration():
    state = ci.create_initial_patient_state(case_id="TEST-03", patient_id="P-03")
    state = ci.PatientStateManager.update_hpi_parameter(state, "duration", "2 weeks", source="patient_voice")
    assert state["hpi"]["duration"]["value"] == "2 weeks"

    state = ci.PatientStateManager.correct_fact(state, "duration", "2 days", corrected_by="patient", reason="Mistaken statement")
    assert state["hpi"]["duration"]["value"] == "2 days"
    assert len(state["provenance_log"]) >= 1
    assert state["provenance_log"][-1]["action"] == "correction"

def test_contradiction_patient_denies_meds_but_document_has_prescription():
    state = ci.create_initial_patient_state(case_id="TEST-04", patient_id="P-04")
    state["medications"] = ["none"]
    state["medications_queried"] = True

    doc_data = {
        "medications": ["Metformin 500mg", "Atorvastatin 10mg"],
        "raw_text": "Rx: Metformin 500mg BD, Atorvastatin 10mg HS"
    }
    contras = ci.ContradictionEngine.check_document_vs_patient(state, doc_data)
    assert len(contras) > 0
    assert contras[0]["category"] == "medications"
    assert contras[0]["severity"] == "HIGH"

def test_contradiction_allergy_denial():
    state = ci.create_initial_patient_state(case_id="TEST-05", patient_id="P-05")
    state["allergies"] = ["no allergies"]
    doc_data = {
        "allergies": ["Penicillin"],
        "raw_text": "Allergies: Severe rash with Penicillin"
    }
    contras = ci.ContradictionEngine.check_document_vs_patient(state, doc_data)
    assert any(c["category"] == "allergies" for c in contras)


# ==============================================================================
# 7. PROVENANCE TRACKER & MEDICAL TIMELINE
# ==============================================================================

def test_provenance_entry_creation():
    entry = ci.ProvenanceTracker.create_provenance_entry("severity", 8, "patient_voice", 0.95, "pain 8/10")
    assert entry["source"] == "patient_voice"
    assert entry["value"] == 8
    assert entry["confidence"] == 0.95

def test_timeline_synthesis():
    state = ci.create_initial_patient_state(case_id="TEST-06", patient_id="P-06")
    state["chief_complaint"] = "Fever and cough"
    state = ci.PatientStateManager.update_hpi_parameter(state, "duration", "3 days", source="patient_voice")
    state = ci.PatientStateManager.update_hpi_parameter(state, "associated_symptoms", ["Chills", "Bodyache"], source="patient_voice")

    timeline = ci.ProvenanceTracker.synthesize_timeline(state)
    assert len(timeline) >= 2
    assert any("Fever and cough" in ev["event"] for ev in timeline)


# ==============================================================================
# 8. CLINICAL SUMMARY SYNTHESIZER & COMPLETENESS METER
# ==============================================================================

def test_completeness_meter():
    state = ci.create_initial_patient_state(case_id="TEST-07", patient_id="P-07")
    comp_initial = ci.ClinicalSummarySynthesizer.calculate_completeness(state)
    assert comp_initial["score_percent"] < 30

    state["chief_complaint"] = "Headache"
    state = ci.PatientStateManager.update_hpi_parameter(state, "duration", "2 days", source="patient_voice")
    state = ci.PatientStateManager.update_hpi_parameter(state, "severity", 7, source="patient_voice")
    state = ci.PatientStateManager.update_hpi_parameter(state, "location", "forehead", source="patient_voice")
    comp_updated = ci.ClinicalSummarySynthesizer.calculate_completeness(state)
    assert comp_updated["score_percent"] > comp_initial["score_percent"]

def test_quick_snapshot_generation():
    state = ci.create_initial_patient_state(case_id="TEST-08", patient_id="P-08")
    state["chief_complaint"] = "Acute chest discomfort"
    state = ci.PatientStateManager.update_hpi_parameter(state, "duration", "2 hours", source="patient_voice")
    state = ci.PatientStateManager.update_hpi_parameter(state, "severity", 9, source="patient_voice")

    snapshot = ci.ClinicalSummarySynthesizer.generate_quick_snapshot(state)
    assert "Quick Consultation Snapshot" in snapshot["title"]
    assert "Acute chest discomfort" in snapshot["chief_complaint"]
    assert "DRAFT" in snapshot["disclaimer"]
    assert len(snapshot["provisional_differentials"]) > 0


# ==============================================================================
# 9. PATIENT PRIVACY GUARDS (NO PIN/PASSWORD LEAKAGE)
# ==============================================================================

def test_patient_privacy_sanitizes_pii():
    state = ci.create_initial_patient_state(case_id="TEST-09", patient_id="P-09")
    state["access_pin"] = "PIN-1234"
    state["password_hash"] = "secret_hash"

    sanitized_patient = ci.PatientStateManager.sanitize_for_export(state, is_physician_view=False)
    assert "access_pin" not in sanitized_patient
    assert "password_hash" not in sanitized_patient

    sanitized_doctor = ci.PatientStateManager.sanitize_for_export(state, is_physician_view=True)
    assert "password_hash" not in sanitized_doctor


# ==============================================================================
# 10. FULL REST API ENDPOINT INTEGRATION
# ==============================================================================

def test_api_interview_start():
    resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN",
        "chief_complaint": "Persistent headache"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert "case_id" in data
    assert "current_question" in data
    assert "Please tell me in your own words" in data["current_question"]["question"]["en-IN"]

def test_api_interview_respond_and_gap_analysis():
    # 1. Start interview
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # 2. Patient gives answer containing complaint and duration in one shot
    resp1 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I have had fever for 4 days",
        "language_code": "en-IN",
        "input_mode": "voice"
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] in ["active", "completed"]
    assert "extracted_entities" in data1
    assert data1["extracted_entities"]["duration"]["value"] == "4 days"

def test_api_interview_red_flag_interruption():
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I have crushing chest pain radiating to my left arm",
        "language_code": "en-IN",
        "input_mode": "voice"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PAUSED_RED_FLAG"
    assert data["urgency"] == "CRITICAL"
    assert "Immediate Attention Required" in data["message"]

def test_api_interview_correct_fact():
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # Post initial answer
    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "fever for 10 days",
        "language_code": "en-IN"
    })

    # Rectify fact
    corr_resp = client.post("/api/cases/interview/correct-fact", json={
        "case_id": case_id,
        "parameter_name": "duration",
        "corrected_value": "2 days",
        "correction_reason": "Patient misspoke earlier"
    })
    assert corr_resp.status_code == 200
    assert corr_resp.json()["new_value"] == "2 days"

def test_api_interview_verify_document():
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # Patient says no meds
    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I do not take any regular medications",
        "language_code": "en-IN"
    })

    # Uploaded doc has Metformin
    doc_resp = client.post("/api/cases/interview/verify-document", json={
        "case_id": case_id,
        "document_data": {
            "medications": ["Metformin 500mg"],
            "raw_text": "Rx: Metformin 500mg daily"
        }
    })
    assert doc_resp.status_code == 200
    assert doc_resp.json()["count"] > 0

def test_api_interview_review_and_finalize():
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "PAT-1001",
        "language_code": "en-IN",
        "chief_complaint": "Persistent cough and low grade fever"
    })
    case_id = start_resp.json()["case_id"]

    # Provide duration and severity
    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "It started 5 days ago and pain is 4 out of 10",
        "language_code": "en-IN"
    })

    # Fetch review package
    rev_resp = client.get(f"/api/cases/interview/{case_id}/review")
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert "quick_snapshot" in rev_data
    assert "detailed_case_history" in rev_data
    assert rev_data["status"] == "READY_FOR_PHYSICIAN_VERIFICATION"

    # Finalize case
    fin_resp = client.post(f"/api/cases/interview/{case_id}/finalize")
    assert fin_resp.status_code == 200
    assert fin_resp.json()["status"] == "finalized"
