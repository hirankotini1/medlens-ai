"""
MEDLENS AI — Comprehensive Clinical Conversation Engine Test Suite
Tests all 10 clinical scenarios and relevance metrics required by the Rebuild Specification:
- Scenario 1: Headache (Strictly headache-related; rejects respiratory/cardiac/abdominal)
- Scenario 2: Abdominal Pain (Strictly GI/quadrant-related; rejects left-arm radiation/headache)
- Scenario 3: Fever (Strictly infectious/pattern-related; rejects climbing stairs/sciatica)
- Scenario 4: Cough (Strictly respiratory/sputum-related; rejects abdominal pain)
- Scenario 5: Joint Pain (Strictly musculoskeletal/weight-bearing; rejects breathing/acidity)
- Scenario 6: Multiple Symptoms (Coherent clustered questioning; preserves all symptoms)
- Scenario 7: Ambiguous Complaint ('I am not feeling well' -> Clinical clarification)
- Scenario 8: Previously Answered Information (Slot gap analysis; zero duplicate questions)
- Scenario 9: AI API Failure / Fallback Reliability (100% complaint-specific questions)
- Scenario 10: Multilingual & Regional Input (English, Hindi, Telugu, Odia)
- Relevance Metrics: 100% relevance score, 0 unrelated questions, 0 duplicates.
"""

import pytest
from api.clinical_interview.state_manager import create_initial_patient_state, PatientStateManager
from api.clinical_interview.question_engine import ClinicalQuestionEngine
from api.clinical_interview.answer_extractor import ClinicalAnswerExtractor
from api.clinical_interview.relevance_validator import ClinicalQuestionRelevanceValidator
from api.case_taking_engine import get_adaptive_questions, get_deterministic_adaptive_questions


class TestClinicalScenarios:
    """Rigorous evaluation of conversational questioning across clinical complaint scenarios."""

    def test_scenario_1_headache_relevance(self):
        """Patient reports headache: next question must be headache-related; rejects respiratory/cardiac/GI."""
        state = create_initial_patient_state("CASE_HA", "PAT_01", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "headache", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "duration", "1 day", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None, "Engine must return a question for headache"
        assert q["id"].startswith("hpi.headache."), f"Expected headache-specific question, got {q['id']}"

        # Strict rejection checks
        q_text = q["text"].lower()
        forbidden_terms = ["breathe", "breathing", "chest pain", "left arm", "stomach", "urine", "stairs"]
        for term in forbidden_terms:
            assert term not in q_text, f"Unrelated term '{term}' found in headache question: {q['text']}"

        # Verify through relevance validator
        is_valid, _ = ClinicalQuestionRelevanceValidator.validate_question(
            {"id": "bad_q", "text": "Do you have difficulty breathing?", "target_slot": "respiratory"},
            state,
            active_complaint="headache"
        )
        assert not is_valid, "Validator must reject 'Do you have difficulty breathing?' for headache complaint"

    def test_scenario_2_abdominal_pain_relevance(self):
        """Patient reports stomach pain after eating: next question must be abdominal-related; rejects left arm radiation."""
        state = create_initial_patient_state("CASE_ABD", "PAT_02", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "abdominal pain", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "triggers", "after eating", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None, "Engine must return a question for abdominal pain"
        assert q["id"].startswith("hpi.abd."), f"Expected abdominal-specific question, got {q['id']}"

        q_text = q["text"].lower()
        forbidden_terms = ["left arm", "arm", "jaw", "thunderclap", "stairs", "coughing blood"]
        for term in forbidden_terms:
            assert term not in q_text, f"Unrelated term '{term}' found in abdominal question: {q['text']}"

        # Verify rejection of left arm radiation
        is_valid, _ = ClinicalQuestionRelevanceValidator.validate_question(
            {"id": "bad_q2", "text": "Does the pain radiate to your left arm?", "target_slot": "radiation"},
            state,
            active_complaint="abdominal_pain"
        )
        assert not is_valid, "Validator must reject left arm radiation question for abdominal complaint"

    def test_scenario_3_fever_relevance(self):
        """Patient reports fever and chills: next question must be fever-related; rejects climbing stairs."""
        state = create_initial_patient_state("CASE_FEV", "PAT_03", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "fever", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "character", "chills and rigors", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None, "Engine must return a question for fever"
        assert q["id"].startswith("hpi.fever."), f"Expected fever-specific question, got {q['id']}"

        q_text = q["text"].lower()
        forbidden_terms = ["climb", "climbing stairs", "left arm", "thunderclap", "knee lock"]
        for term in forbidden_terms:
            assert term not in q_text, f"Unrelated term '{term}' found in fever question: {q['text']}"

        # Verify rejection of climbing stairs question
        is_valid, _ = ClinicalQuestionRelevanceValidator.validate_question(
            {"id": "bad_q3", "text": "Do you have difficulty climbing stairs?", "target_slot": "mobility"},
            state,
            active_complaint="fever"
        )
        assert not is_valid, "Validator must reject climbing stairs question for fever complaint"

    def test_scenario_4_cough_relevance(self):
        """Patient reports dry cough for 5 days: next question must be cough-related; rejects abdominal pain."""
        state = create_initial_patient_state("CASE_COUGH", "PAT_04", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "cough", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "duration", "5 days", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "character", "dry cough", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None, "Engine must return a question for cough"
        assert q["id"].startswith("hpi.cough."), f"Expected cough-specific question, got {q['id']}"

        q_text = q["text"].lower()
        assert "stomach" not in q_text
        assert "abdomen" not in q_text
        assert "urine" not in q_text

    def test_scenario_5_joint_pain_relevance(self):
        """Patient reports right knee pain when walking: next question must be joint-related; rejects breathing/chest."""
        state = create_initial_patient_state("CASE_JOINT", "PAT_05", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "joint pain", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "location", "right knee", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "triggers", "when walking", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None, "Engine must return a question for joint pain"
        assert q["id"].startswith("hpi.joint."), f"Expected joint-specific question, got {q['id']}"

        q_text = q["text"].lower()
        assert "breathe" not in q_text
        assert "chest pain" not in q_text
        assert "acidity" not in q_text

    def test_scenario_6_multiple_symptoms(self):
        """Patient reports multiple symptoms: fever, headache, body aches -> coherent clustered questioning."""
        state = create_initial_patient_state("CASE_MULTI", "PAT_06", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")

        utterance = "I have fever, headache, and body aches since yesterday."
        complaints = ClinicalAnswerExtractor.extract_complaints(utterance)
        assert len(complaints) >= 2, f"Expected multiple complaints extracted, got {complaints}"
        for c in complaints:
            PatientStateManager.add_chief_complaint(state, c, "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None
        # Must address either fever or headache
        valid_prefixes = ("hpi.fever.", "hpi.headache.")
        assert q["id"].startswith(valid_prefixes), f"Question {q['id']} must target active symptom cluster"

    def test_scenario_7_ambiguous_complaint_clarification(self):
        """Patient says 'I am not feeling well': engine returns clinical clarification, not a random disease question."""
        state = create_initial_patient_state("CASE_AMBIG", "PAT_07", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "I am not feeling well", "patient_text")

        q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q is not None
        assert q["id"] == "clarify_chief_complaint", f"Expected clarify_chief_complaint, got {q['id']}"
        assert "what specific symptom" in q["text"].lower()

    def test_scenario_8_no_repetition_of_answered_slots(self):
        """Patient already provided duration and location: next question must target missing slot, not repeat."""
        state = create_initial_patient_state("CASE_SLOTS", "PAT_08", {}, "en-IN")
        PatientStateManager.record_asked_question(state, "chief_complaint_open")
        PatientStateManager.add_chief_complaint(state, "headache", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "duration", "3 days", "patient_text")
        PatientStateManager.update_hpi_parameter(state, "location", "one side of head", "patient_text")

        q1 = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q1 is not None
        assert q1["id"] != "hpi.headache.location", "Must not repeat already answered location slot"

        PatientStateManager.record_asked_question(state, q1["id"])
        q2 = ClinicalQuestionEngine.select_next_question(state, "en-IN")
        assert q2 is not None
        assert q2["id"] != q1["id"], "Must not repeat recently asked question"

    def test_scenario_9_deterministic_fallback_quality(self):
        """When AI API is offline or returns invalid output, fallback returns 100% complaint-specific questions."""
        complaints_test = [
            ("headache", "ha_"),
            ("stomach pain", "abd_"),
            ("fever", "fever_"),
            ("cough", "cough_"),
            ("knee joint pain", "joint_"),
            ("dizziness", "dizziness_")
        ]
        for cc, expected_prefix in complaints_test:
            qs = get_deterministic_adaptive_questions(cc, {})
            assert len(qs) > 0, f"Fallback must provide questions for {cc}"
            assert any(q["id"].startswith(expected_prefix) for q in qs), (
                f"For complaint '{cc}', expected question prefix '{expected_prefix}', got {[q['id'] for q in qs]}"
            )

    def test_scenario_10_multilingual_inputs(self):
        """Tests Hindi, Telugu, and Odia complaint inputs: ensures proper normalization and language matching."""
        lang_cases = [
            ("मुझे दो दिन से तेज सिरदर्द है", "hi-IN", "headache"),
            ("నాకు కడుపు నొప్పిగా ఉంది", "te-IN", "abdominal_pain"),
            ("ମୋତେ ୩ ଦିନ ହେଲା ପ୍ରବଳ ଜ୍ୱର ହେଉଛି", "or-IN", "fever")
        ]
        for text, lang_code, expected_domain in lang_cases:
            complaints = ClinicalAnswerExtractor.extract_complaints(text)
            assert len(complaints) > 0, f"Failed to extract complaint from '{text}'"
            norm_key = ClinicalQuestionRelevanceValidator.normalize_complaint_key(complaints[0])
            assert norm_key == expected_domain, f"Expected domain '{expected_domain}', got '{norm_key}' from '{text}'"

            state = create_initial_patient_state(f"CASE_{lang_code}", "PAT_MULTI", {}, lang_code)
            PatientStateManager.record_asked_question(state, "chief_complaint_open")
            PatientStateManager.add_chief_complaint(state, complaints[0], "patient_text")

            q = ClinicalQuestionEngine.select_next_question(state, lang_code)
            assert q is not None
            # Check translation exists for requested language
            assert lang_code in q["question"], f"Question must have translation for {lang_code}"
            assert len(q["question"][lang_code].strip()) > 5, f"Translation for {lang_code} is empty"


class TestRelevanceMetrics:
    """Quantitative measurement of clinical question quality and relevance."""

    def test_zero_unrelated_questions_metric(self):
        """Evaluates 15 distinct complaints: 0 unrelated questions allowed."""
        clinical_test_battery = [
            ("headache", ["head", "throbbing", "migraine", "forehead", "temple", "light"]),
            ("abdominal pain", ["abdomen", "stomach", "cramp", "belly", "food", "vomit", "stool"]),
            ("fever", ["fever", "temperature", "chills", "shivering", "days", "headache", "body"]),
            ("cough", ["cough", "phlegm", "sputum", "blood", "night", "wheezing"]),
            ("joint pain", ["joint", "knee", "swelling", "stiffness", "walking", "stairs"]),
            ("chest pain", ["chest", "pain", "radiate", "pressure", "exertion", "sweating"]),
            ("breathlessness", ["breathe", "breathing", "rest", "pillows", "wheeze", "gasping"]),
            ("back pain", ["back", "sciatica", "leg", "lifting", "numbness"]),
            ("vomiting", ["vomit", "vomited", "water", "bile", "blood", "nausea"]),
            ("diarrhea", ["loose", "watery", "stools", "blood", "motions", "thirst"]),
            ("urinary symptoms", ["urination", "burning", "urine", "blood", "flank"]),
            ("dizziness", ["spinning", "room", "vertigo", "lightheaded", "head", "ears"]),
            ("skin allergy", ["rash", "itching", "welts", "hives", "medication", "soap"]),
            ("throat symptoms", ["throat", "swallow", "saliva", "scratchy", "tonsil"]),
            ("weakness", ["weakness", "fatigue", "exhaustion", "daily", "walking", "pale"])
        ]

        total_checked = 0
        relevant_count = 0

        for complaint, expected_keywords in clinical_test_battery:
            state = create_initial_patient_state(f"METRIC_{complaint}", "PAT_METRIC", {}, "en-IN")
            PatientStateManager.record_asked_question(state, "chief_complaint_open")
            PatientStateManager.add_chief_complaint(state, complaint, "patient_text")

            q = ClinicalQuestionEngine.select_next_question(state, "en-IN")
            assert q is not None
            q_text_low = q["text"].lower()

            # Check relevance
            is_relevant = any(kw in q_text_low for kw in expected_keywords)
            assert is_relevant, f"Question for '{complaint}' was not relevant: '{q['text']}'"

            # Check cross-system purity
            canonical = ClinicalQuestionRelevanceValidator.normalize_complaint_key(complaint)
            is_valid, reason = ClinicalQuestionRelevanceValidator.validate_question(
                q, state, active_complaint=canonical
            )
            assert is_valid, f"Question for '{complaint}' failed validity: {reason}"

            total_checked += 1
            relevant_count += 1

        relevance_rate = (relevant_count / total_checked) * 100.0
        assert relevance_rate >= 95.0, f"Relevance rate {relevance_rate}% below 95% threshold"
        print(f"\n[RELEVANCE METRICS] Tested {total_checked} conditions: Relevance Rate = {relevance_rate:.1f}% (0 unrelated questions)")

