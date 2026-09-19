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


# ==============================================================================
# 11. REQUIRED CLINICAL INTERVIEW SCENARIOS (TEST 1 - 11)
# ==============================================================================

def test_scenario_1_start_interview_open_ended():
    """TEST 1: Start interview -> expected open-ended first question."""
    resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-01",
        "language_code": "en-IN"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["started", "active"]
    first_q = data["current_question"]
    assert first_q["id"] in ["chief_complaint_open", "core.open_ended_complaint"]
    assert "in your own words" in (first_q.get("question", {}).get("en-IN") or first_q.get("text", ""))

def test_scenario_2_information_gap_chest_pain_duration():
    """TEST 2: Answer severe chest pain since yesterday -> next question must NOT ask duration again."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-02",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I have severe chest pain since yesterday",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN",
        "input_mode": "voice"
    })
    assert resp.status_code == 200
    data = resp.json()
    extracted = data["extracted_entities"]
    complaints = extracted.get("chief_complaints", {}).get("value", [])
    if not complaints and extracted.get("complaint", {}).get("value"):
        complaints = [extracted["complaint"]["value"]]
    complaint_text = " ".join(complaints).lower()
    assert "chest pain" in complaint_text
    assert extracted.get("severity", {}).get("value") in [7, "7", "severe"]
    assert "day" in str(extracted.get("duration", {}).get("value", "")).lower() or "yesterday" in str(extracted.get("duration", {}).get("value", "")).lower()

    # Next question must NOT be duration
    if data["next_question"]:
        assert data["next_question"]["id"] != "cardio.onset_duration"
        assert data["next_question"]["id"] != "hpi.duration"

def test_scenario_3_radiation_breathlessness_exertional():
    """TEST 3: Radiation + breathlessness when walking -> missing info identifies character/onset/associated."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-03",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp1 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I have chest discomfort for two days",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })
    q1_id = resp1.json()["next_question"]["id"]

    resp2 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "Pain spreads to my left arm and I feel breathless when walking.",
        "current_question_id": q1_id,
        "language_code": "en-IN"
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    state = data2["state"]
    # Radiation, breathlessness, exertional relationship extracted
    assert state.get("hpi", {}).get("radiation") is not None
    assert "arm" in str(state.get("hpi", {}).get("radiation")).lower()

def test_scenario_4_red_flag_pause():
    """TEST 4: Answer a red-flag statement -> interview paused (PAUSED_RED_FLAG)."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-04",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I have severe crushing central chest pain radiating to left jaw and profuse sweating",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PAUSED_RED_FLAG"
    assert data["urgency"] in ["CRITICAL", "EMERGENT"]
    assert "Immediate Attention Required" in data["message"]

def test_scenario_5_no_duplicate_questions():
    """TEST 5: Answer the same question twice -> no duplicate question returned."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-05",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp1 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "mild headache",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })
    data1 = resp1.json()
    q1 = data1.get("next_question")
    if q1:
        resp2 = client.post("/api/cases/interview/respond", json={
            "case_id": case_id,
            "answer_text": "mild headache again",
            "current_question_id": q1["id"],
            "language_code": "en-IN"
        })
        data2 = resp2.json()
        q2 = data2.get("next_question")
        if q2:
            assert q2["id"] != q1["id"]
            assert q2["id"] != "chief_complaint_open"

def test_scenario_6_multiple_complaints_preserved():
    """TEST 6: Multiple complaint 'fever and cough for three days' -> two complaints preserved."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-06",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "fever and cough for three days",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })
    assert resp.status_code == 200
    data = resp.json()
    state = data["state"]
    chief_complaints = state.get("chief_complaints", [])
    complaints_str = " ".join([c.lower() for c in chief_complaints])
    assert "fever" in complaints_str
    assert "cough" in complaints_str

def test_scenario_7_medication_contradiction_document():
    """TEST 7: Patient says 'No medicines', document has Metformin -> discrepancy flag."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-07",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I do not take any regular medicines, no medications at all.",
        "current_question_id": "med.current_reconciliation",
        "language_code": "en-IN"
    })

    doc_resp = client.post("/api/cases/interview/verify-document", json={
        "case_id": case_id,
        "document_data": {
            "medications": ["Metformin 500mg"],
            "raw_text": "Rx: Metformin 500mg BD for Type 2 Diabetes"
        }
    })
    assert doc_resp.status_code == 200
    data = doc_resp.json()
    assert data["count"] > 0
    contradiction = data["contradictions_detected"][0]
    contra_str = (contradiction.get("discrepancy_description", "") + " " + contradiction.get("document_claim", "") + " " + contradiction.get("document_evidence", "")).lower()
    assert "metformin" in contra_str

def test_scenario_8_patient_correction_recalculation():
    """TEST 8: Patient correction: change 3 days -> 3 weeks -> state updated & completeness recalculated."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-08",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "stomach pain for 3 days",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })

    corr_resp = client.post("/api/cases/interview/correct-fact", json={
        "case_id": case_id,
        "parameter_name": "duration",
        "corrected_value": "3 weeks",
        "correction_reason": "Patient corrected duration statement"
    })
    assert corr_resp.status_code == 200
    data = corr_resp.json()
    assert data["new_value"] == "3 weeks"
    assert "completeness" in data
    assert data["completeness"]["score_percent"] > 0

def test_scenario_9_telugu_language_localization():
    """TEST 9: Telugu language -> question returned in Telugu or safe fallback."""
    resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-09",
        "language_code": "te-IN"
    })
    assert resp.status_code == 200
    data = resp.json()
    first_q = data["current_question"]
    assert "te-IN" in first_q.get("question", {})
    assert "సమస్య" in first_q["question"]["te-IN"] or "బాధ" in first_q["question"]["te-IN"]

def test_scenario_10_touch_input_mode_equality():
    """TEST 10: Touch input mode routes to exact same interview engine path."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-10",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "Fever / 2-3 days",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN",
        "input_mode": "touch"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["active", "completed"]
    assert "extracted_entities" in data

def test_scenario_11_complete_interview_review_finalize_doctor_package():
    """TEST 11: Complete interview -> review -> finalize -> doctor package with all required fields."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-11",
        "language_code": "en-IN",
        "chief_complaint": "Joint pain"
    })
    case_id = start_resp.json()["case_id"]

    # Post answers
    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "Severe knee joint pain for 2 weeks, worse on walking",
        "current_question_id": "chief_complaint_open",
        "language_code": "en-IN"
    })

    # Review package
    rev_resp = client.get(f"/api/cases/interview/{case_id}/review")
    assert rev_resp.status_code == 200
    pkg = rev_resp.json()
    assert "quick_snapshot" in pkg
    assert "detailed_case_history" in pkg
    assert "contradictions" in pkg
    assert "uncertainties" in pkg
    assert "red_flags" in pkg
    assert "transcripts" in pkg
    assert "source_provenance" in pkg
    assert pkg["status"] == "READY_FOR_PHYSICIAN_VERIFICATION"

    # Finalize
    fin_resp = client.post(f"/api/cases/interview/{case_id}/finalize")
    assert fin_resp.status_code == 200
    fin_data = fin_resp.json()
    assert fin_data["status"] == "finalized"
    assert "triage_urgency" in fin_data


def test_scenario_12_patient_answer_count_limit():
    """TEST 12: Reaching max_patient_answers limit safely completes intake without inventing data."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-LIMIT",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # Directly set a low max_patient_answers to test limit handling
    state = db.get_case_interview_state(case_id)
    state["max_patient_answers"] = 3
    db.save_case_interview_state(case_id, state)

    # 3 answers
    r1 = client.post("/api/cases/interview/respond", json={"case_id": case_id, "answer_text": "Fever", "language_code": "en-IN"})
    assert r1.json()["patient_answer_count"] == 1
    assert r1.json()["is_complete"] is False

    r2 = client.post("/api/cases/interview/respond", json={"case_id": case_id, "answer_text": "3 days", "language_code": "en-IN"})
    assert r2.json()["patient_answer_count"] == 2

    r3 = client.post("/api/cases/interview/respond", json={"case_id": case_id, "answer_text": "Moderate", "language_code": "en-IN"})
    data3 = r3.json()
    assert data3["patient_answer_count"] == 3
    assert data3["is_complete"] is True
    assert "limit" in data3["state"].get("limit_reached_note", "").lower()


def test_scenario_13_document_request_ecg():
    """TEST 13: Mentioning ECG triggers intelligent document request with localized prompt."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-ECG",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I had chest pain and the clinic took an ECG yesterday.",
        "language_code": "en-IN"
    })
    data = resp.json()
    assert "document_request" in data
    doc_req = data["document_request"]
    assert doc_req is not None
    assert doc_req["should_request"] is True
    assert doc_req["request_type"] == "ecg_report"
    assert "ECG" in doc_req["display_prompt"]


def test_scenario_14_document_request_fever_cbc():
    """TEST 14: Mentioning CBC or blood test triggers lab_report request."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-CBC",
        "language_code": "hi-IN"
    })
    case_id = start_resp.json()["case_id"]

    resp = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "मुझे बुखार है और मैंने खून की जांच (blood test) करवाई थी।",
        "language_code": "hi-IN"
    })
    data = resp.json()
    doc_req = data.get("document_request")
    assert doc_req is not None
    assert doc_req["request_type"] == "lab_report"
    assert "जांच" in doc_req["display_prompt"]


def test_scenario_15_document_request_skip():
    """TEST 15: Skipping a document request records it and does not repeat prompt."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-SKIP",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # Trigger ECG request
    r1 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "I had an ECG yesterday",
        "language_code": "en-IN"
    })
    doc_req = r1.json().get("document_request")
    assert doc_req is not None
    req_id = doc_req["request_id"]

    # Skip document request
    skip_resp = client.post("/api/cases/interview/skip-document-request", json={
        "case_id": case_id,
        "request_id": req_id
    })
    assert skip_resp.status_code == 200
    assert skip_resp.json()["status"] == "skipped"

    # Subsequent mention does not re-request the same skipped document
    r2 = client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "The ecg showed normal rate",
        "language_code": "en-IN"
    })
    assert r2.json().get("document_request") is None


def test_scenario_16_document_upload_ocr_updates_state():
    """TEST 16: Uploading a prescription via upload endpoint extracts medicines and updates state."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-UPLOAD",
        "language_code": "en-IN"
    })
    case_id = start_resp.json()["case_id"]

    # Create mock text prescription
    prescription_text = "Prescription: Tab Metformin 500mg BD. Tab Atorvastatin 20mg OD."
    files = {"file": ("rx_record.txt", prescription_text.encode("utf-8"), "text/plain")}
    data = {"document_type": "prescription"}

    upload_resp = client.post(f"/api/cases/{case_id}/upload-and-attach-file", files=files, data=data)
    assert upload_resp.status_code == 200
    res_data = upload_resp.json()
    assert "state" in res_data
    meds = res_data["state"].get("medications", [])
    assert any("metformin" in str(m).lower() for m in meds)


def test_scenario_17_pdf_generation_endpoint():
    """TEST 17: GET /api/cases/{case_id}/report.pdf generates clean A4 PDF."""
    start_resp = client.post("/api/cases/interview/start", json={
        "patient_id": "P-TEST-PDF",
        "language_code": "en-IN",
        "chief_complaint": "Severe persistent headache"
    })
    case_id = start_resp.json()["case_id"]

    # Post an answer
    client.post("/api/cases/interview/respond", json={
        "case_id": case_id,
        "answer_text": "Throbbing headache for 3 days, severity 8/10",
        "language_code": "en-IN"
    })

    # Request PDF
    pdf_resp = client.get(f"/api/cases/{case_id}/report.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 500  # Valid binary PDF
    assert pdf_resp.content.startswith(b"%PDF")
    assert "attachment" in pdf_resp.headers.get("content-disposition", "")


def test_scenario_18_multilingual_pdf_generation():
    """TEST 18: PDF generator handles multilingual Unicode data (Hindi, Telugu, Odia)."""
    report_data = {
        "case": {
            "case_id": "CASE-MULTI-UNICODE",
            "created_at": "2026-09-19",
            "status": "Ready for Physician Review",
            "language": "Hindi / Telugu / Odia",
            "input_mode": "Multilingual Voice",
            "chief_complaint": "छाती में दर्द / గుండె నొప్పి / ଛାତିରେ ଯନ୍ତ୍ରଣା"
        },
        "patient": {
            "name": "राधा शर्मा / రాధా శర్మ",
            "age": "45",
            "gender": "Female",
            "patient_id": "P-UNICODE-99",
            "abha_id": "91-1234-5678-9999"
        },
        "chief_complaints": [
            "छाती में दर्द (Chest pain)",
            "తీవ్రమైన దగ్గు (Severe cough)",
            "ଜ୍ୱର ଏବଂ ଦୁର୍ବଳତା (Fever and weakness)"
        ],
        "history": {
            "hpi": {"onset": "2 days ago", "severity": "7/10"},
            "past_medical_history": "मधुमेह (Diabetes Mellitus)",
            "family_history": "హృద్రోగం (Heart Disease)"
        },
        "medications": ["Metformin 500mg"],
        "allergies": ["No known allergies"],
        "documents": [],
        "red_flags": [],
        "information_gaps": ["Blood pressure not recorded"],
        "contradictions": [],
        "interview_summary": {"turn_count": 5, "patient_answer_count": 5},
        "ai_analysis": {"recommended_workup": ["12-Lead ECG", "Blood Glucose Check"]},
        "doctor_review": {}
    }

    pdf_bytes = ci.generate_clinical_pdf(report_data)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


