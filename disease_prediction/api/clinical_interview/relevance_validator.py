"""
MEDLENS AI — Clinical Question Relevance & Context Validator
Authoritative Multi-Layer Validation Engine:
1. Chief Complaint Grounding: Ensures questions strictly relate to the active complaint.
2. Cross-System Jump Prohibition: Rejects questions introducing unrelated organ systems.
3. Information Gap & Slot Verification: Ensures questions target missing, uncollected slots.
4. Redundancy & Duplicate Prevention: Rejects previously asked questions and answered parameters.
5. Safety, Non-Diagnostic & Scope Boundaries: Rejects diagnostic assertions, prescriptions, or false reassurance.
6. Ambiguity Detection & Clarification Dispatcher: Detects vague inputs and routes to focused clarifications.
"""

import re
from typing import Dict, Any, List, Optional, Set, Tuple

# Ambiguous / Non-specific patient statements that require clarification
AMBIGUOUS_PATTERNS = [
    r"^(i\s*am\s*|i['’]?m\s*)?(not\s*feeling\s*well|unwell|sick|ill|feeling\s*bad|feeling\s*down)\b",
    r"^(tabiyat\s*kharab|theek\s*nahi\s*hai|achha\s*nahi\s*lag\s*raha|kuch\s*theek\s*nahi)\b",
    r"^(bagoledu|baaledu|health\s*baaledu|asoukarryam)\b",
    r"^(bholo\s*laguni|deha\s*kharap|asubidha\s*hauchhi)\b",
    r"^(udambu\s*seriyillai|nallaa\s*illai)\b",
    r"^(something\s*is\s*wrong|body\s*problem|medical\s*issue|health\s*problem)\b",
    r"^(help\s*me|i\s*need\s*help|consult\s*doctor|doctor\s*please)\b"
]

# Strict Cross-System Prohibitions: Disallowed terms for each active clinical complaint
DISALLOWED_TERMS_BY_COMPLAINT: Dict[str, List[str]] = {
    "headache": [
        "difficulty breathing", "shortness of breath", "breathless", "breathe", "wheez", "stridor",
        "chest pain", "radiat.*left arm", "left arm", "jaw pain", "angina", "heart attack",
        "stomach pain", "abdomen", "belly", "loose stool", "diarrhea", "constipat",
        "urine", "urinary", "dysuria", "burning urination",
        "climb.*stairs", "stairs", "walking distance",
        "knee pain", "joint swelling", "skin rash"
    ],
    "abdominal_pain": [
        "radiat.*left arm", "left arm", "shoulder blade", "jaw pain", "angina", "crushing chest",
        "thunderclap", "headache", "migraine", "visual aura",
        "climb.*stairs", "stairs", "knee", "joint swelling",
        "coughing.*phlegm", "sputum", "coughing blood", "hemoptysis", "wheez",
        "sciatica", "leg numbness"
    ],
    "fever": [
        "climb.*stairs", "stairs", "walking distance",
        "radiat.*left arm", "left arm", "thunderclap", "sciatica",
        "knee lock", "food cravings", "ear discharge"
    ],
    "cough": [
        "stomach pain", "abdomen", "belly", "loose stool", "diarrhea",
        "burning urination", "urine", "dysuria",
        "radiat.*left arm", "left arm", "jaw pain",
        "joint swelling", "knee pain", "sciatica"
    ],
    "joint_pain": [
        "difficulty breathing", "shortness of breath", "breathless",
        "coughing blood", "hemoptysis", "sputum",
        "chest pain", "radiat.*left arm", "crushing chest",
        "acidity", "loose stool", "diarrhea", "stomach pain"
    ],
    "chest_pain": [
        "joint swelling", "ear ache", "ear discharge", "skin rash", "rash itching",
        "loose stool", "watery diarrhea"
    ],
    "breathlessness": [
        "ear discharge", "joint lock", "skin rash itching", "food cravings"
    ],
    "urinary_symptoms": [
        "thunderclap", "headache", "climbing stairs", "coughing phlegm", "sputum",
        "radiat.*left arm", "ear ache"
    ],
    "dizziness": [
        "diarrhea", "loose stool", "burning urination", "dysuria",
        "coughing phlegm", "sputum"
    ],
    "skin_allergy": [
        "radiat.*left arm", "climbing stairs", "burning urination", "dysuria",
        "sciatica"
    ],
    "back_pain": [
        "coughing blood", "sputum", "ear discharge", "visual aura", "thunderclap"
    ],
    "vomiting": [
        "radiat.*left arm", "jaw pain", "thunderclap", "climbing stairs", "sciatica"
    ],
    "diarrhea": [
        "radiat.*left arm", "jaw pain", "thunderclap", "climbing stairs", "sciatica", "visual aura"
    ],
    "throat_symptoms": [
        "radiat.*left arm", "stomach pain", "diarrhea", "sciatica", "knee swelling"
    ],
    "weakness_fatigue": [
        "ear discharge", "knee lock", "thunderclap"
    ]
}

# Positive target slots that are clinically meaningful
VALID_TARGET_SLOTS = {
    "onset", "duration", "duration_and_onset", "location", "location_and_radiation",
    "location_and_quadrant", "joint_location", "character", "severity", "progression",
    "triggers", "aggravating_and_relieving", "associated_symptoms", "safety_check",
    "clarification", "medications", "allergies", "past_medical", "family_history"
}


class ClinicalQuestionRelevanceValidator:
    """Validates question candidates to ensure 100% clinical relevance and safety."""

    @classmethod
    def is_ambiguous_complaint(cls, text: str) -> bool:
        """Determines if a patient's statement is too vague / non-specific to anchor a disease pathway."""
        if not text or not str(text).strip():
            return True
        clean = str(text).strip().lower()
        if len(clean) < 3:
            return True
        for pattern in AMBIGUOUS_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                # Ensure they haven't followed up with an actual symptom (e.g. "not feeling well, have severe headache")
                has_concrete_symptom = any(sym in clean for sym in [
                    "headache", "fever", "cough", "chest", "stomach", "pain", "vomit",
                    "vomiting", "diarrhea", "breath", "dizzy", "rash", "throat", "urine",
                    "dard", "bukhar", "khansi", "pet", "sar", "chhati", "noppi", "jwaram"
                ])
                if not has_concrete_symptom:
                    return True
        return False

    @classmethod
    def get_clarification_question(cls, language_code: str = "en-IN") -> Dict[str, Any]:
        """Returns a polite, focused clinical clarification prompt to identify the chief complaint."""
        text_map = {
            "en-IN": "To help me understand your condition, what specific symptom or problem is bothering you the most today? (For example: headache, fever, stomach pain, cough, or something else?)",
            "hi-IN": "आपकी स्थिति को बेहतर समझने के लिए, आज आपको सबसे ज्यादा क्या तकलीफ हो रही है? (जैसे: सिरदर्द, बुखार, पेट दर्द, खांसी, या कुछ और?)",
            "te-IN": "మీ పరిస్థితిని స్పష్టంగా అర్థం చేసుకోవడానికి, ఈరోజు మీకు ప్రధానంగా ఏ ఇబ్బంది ఉంది? (ఉదాహరణకు: తలనొప్పి, జ్వరం, కడుపు నొప్పి, దగ్గు లేదా మరేదైనా?)",
            "or-IN": "ଆପଣଙ୍କ ସମସ୍ୟା ଭଲଭାବେ ବୁଝିବା ପାଇଁ, ଆଜି ଆପଣଙ୍କୁ ସବୁଠାରୁ ଅଧିକ କି ଅସୁବିଧା ହେଉଛି? (ଯେପରି: ମୁଣ୍ଡବିନ୍ଧା, ଜ୍ୱର, ପେଟ ଯନ୍ତ୍ରଣା, କାଶ, ବା ଅନ୍ୟ କିଛି?)",
            "ta-IN": "உங்கள் பிரச்னையை சரியாக புரிந்துகொள்ள, இன்று உங்களுக்கு முக்கியமாக என்ன செய்கிறது? (உதாரணமாக: தலைவலி, காய்ச்சல், வயிற்று வலி, இருமல்?)"
        }
        quick_picks = [
            "Headache / सिरदर्द / తలనొప్పి",
            "Fever & chills / बुखार / జ్వరం",
            "Stomach pain / पेट दर्द / కడుపు నొప్పి",
            "Cough & cold / खांसी / దగ్గు",
            "Chest discomfort / सीने में दर्द",
            "Joint pain / जोड़ों का दर्द"
        ]
        chosen_text = text_map.get(language_code, text_map["en-IN"])
        return {
            "id": "clarify_chief_complaint",
            "question_id": "clarify_chief_complaint",
            "section": "Chief Complaint Clarification",
            "priority": "P1",
            "parameter": "chief_complaint",
            "target_slot": "clarification",
            "state_key": "chief_complaint",
            "why_asking": "Identifies your primary clinical complaint so relevant follow-ups can be asked.",
            "text": chosen_text,
            "question": text_map,
            "quick_picks": quick_picks,
            "is_clarification": True,
            "allows_free_speech": True
        }

    @classmethod
    def normalize_complaint_key(cls, complaint: str) -> str:
        """Maps free-text or domain names to canonical complaint keys."""
        if not complaint:
            return "generic"
        c = complaint.lower().strip().replace("-", "_").replace(" ", "_")
        if any(w in c for w in ["headache", "migraine", "head_pain", "sar_dard", "munda_bindha", "talanappi"]):
            return "headache"
        if any(w in c for w in ["abdom", "stomach", "belly", "pet_dard", "pet_re_kasta", "kadupu_noppi", "gut"]):
            return "abdominal_pain"
        if any(w in c for w in ["fever", "pyrexia", "temperature", "chills", "bukhar", "jwaram", "jwar"]):
            return "fever"
        if any(w in c for w in ["cough", "phlegm", "sputum", "khansi", "daggu", "kaasa"]):
            return "cough"
        if any(w in c for w in ["chest", "cardiac", "angina", "heart", "chhati", "seena"]):
            return "chest_pain"
        if any(w in c for w in ["breath", "dyspnea", "sob", "wheez", "stridor", "saans", "swasa"]):
            return "breathlessness"
        if any(w in c for w in ["joint", "knee", "arthritis", "jodon", "godige", "mokaali"]):
            return "joint_pain"
        if any(w in c for w in ["back", "lumbar", "spine", "sciatica", "kamar", "nadumu"]):
            return "back_pain"
        if any(w in c for w in ["vomit", "nausea", "emesis", "ulti", "vaanti", "baanti"]):
            return "vomiting"
        if any(w in c for w in ["diarrhea", "loose_stool", "motions", "dast", "jhada"]):
            return "diarrhea"
        if any(w in c for w in ["urin", "dysuria", "bladder", "peshab", "mutram"]):
            return "urinary_symptoms"
        if any(w in c for w in ["dizzy", "vertigo", "lightheaded", "chakkar", "kallu_thiragadam"]):
            return "dizziness"
        if any(w in c for w in ["skin", "rash", "itch", "allergy", "khujli"]):
            return "skin_allergy"
        if any(w in c for w in ["throat", "sore_throat", "pharyngitis", "gala_kharab"]):
            return "throat_symptoms"
        if any(w in c for w in ["weakness", "fatigue", "tired", "lethargy", "kamzori"]):
            return "weakness_fatigue"
        return c

    @classmethod
    def validate_question(
        cls,
        question_dict: Dict[str, Any],
        state: Dict[str, Any],
        active_complaint: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Runs comprehensive multi-layer validation on a candidate question.
        Returns (is_valid: bool, rejection_reason: str).
        """
        if not isinstance(question_dict, dict):
            return False, "Candidate question is not a dictionary."

        q_id = str(question_dict.get("id") or question_dict.get("question_id") or "").strip()
        q_text = str(question_dict.get("question") or question_dict.get("text") or "").strip()
        if isinstance(question_dict.get("question"), dict):
            q_text = str(question_dict["question"].get("en-IN") or question_dict["question"].get("text") or "").strip()

        if not q_text or len(q_text) < 8:
            return False, "Question text is empty or too short."

        q_text_lower = q_text.lower()

        # 1. Scope Boundary: No diagnosis, prescription, or speculative claims
        forbidden_clinical_statements = [
            r"\byou\s*(have|are\s*suffering\s*from|likely\s*have)\b",
            r"\b(i\s*diagnose|this\s*is\s*diagnosed\s*as|my\s*diagnosis)\b",
            r"\b(take\s*tablet|take\s*medicine|take\s*paracetamol|take\s*antibiotic|i\s*prescribe)\b",
            r"\b(nothing\s*to\s*worry|it\s*is\s*definitely\s*not\s*serious)\b"
        ]
        for pattern in forbidden_clinical_statements:
            if re.search(pattern, q_text_lower):
                return False, f"Question violates scope boundary (contains diagnosis/prescribing): '{pattern}'"

        # 2. Check if question ID has already been asked
        asked_ids = set(state.get("asked_question_ids", []))
        if q_id and q_id in asked_ids:
            return False, f"Question ID '{q_id}' has already been asked in this session."

        # 3. Check if target slot is already known in state
        target_slot = str(question_dict.get("target_slot") or question_dict.get("state_key") or question_dict.get("parameter") or "").strip().lower()
        if target_slot and target_slot not in ["general", "none", ""]:
            hpi = state.get("hpi", {})
            if isinstance(hpi, dict):
                existing_val = hpi.get(target_slot)
                if isinstance(existing_val, dict):
                    existing_val = existing_val.get("value")
                if existing_val is not None and str(existing_val).strip() != "" and str(existing_val).strip().lower() not in ["none", "null", "undefined"]:
                    return False, f"Target clinical slot '{target_slot}' is already known with value '{existing_val}'."

        # 4. Check for duplicate / near-duplicate wording in assistant turns
        transcript = state.get("conversation_transcript", [])
        for turn in transcript:
            if turn.get("speaker") == "assistant":
                past_text = str(turn.get("text") or "").strip().lower()
                if past_text and past_text == q_text_lower:
                    return False, "Identical question text was already delivered to patient."

        # 5. Cross-System Jump Prohibition Check
        # Resolve active complaint
        complaints = state.get("chief_complaints", [])
        if active_complaint:
            canonical_complaint = cls.normalize_complaint_key(active_complaint)
        elif complaints:
            canonical_complaint = cls.normalize_complaint_key(complaints[0])
        else:
            canonical_complaint = "generic"

        disallowed_patterns = DISALLOWED_TERMS_BY_COMPLAINT.get(canonical_complaint, [])
        for dis_pattern in disallowed_patterns:
            if re.search(dis_pattern, q_text_lower, re.IGNORECASE):
                # Verify that the patient hasn't explicitly brought up this symptom as a co-complaint
                patient_mentioned = any(
                    re.search(dis_pattern, str(c).lower(), re.IGNORECASE) for c in complaints
                )
                if not patient_mentioned:
                    return False, (
                        f"Cross-system jump detected: question mentions '{dis_pattern}', "
                        f"which is disallowed for active complaint '{canonical_complaint}'."
                    )

        # 6. Affirmative Grounding Check
        # For non-systemic inquiry (medications/allergies/pmh), verify the question pertains to the complaint
        is_systemic_inquiry = target_slot in ["medications", "allergies", "past_medical", "family_history", "pmh", "med", "allergy", "fh"]
        if not is_systemic_inquiry and canonical_complaint != "generic":
            # Check if domain matches or question text mentions relevant complaint anatomy/concepts
            domain = str(question_dict.get("domain") or "").lower()
            if domain and domain != "generic" and domain != canonical_complaint:
                # If question belongs to another domain not in complaints
                domain_in_complaints = any(cls.normalize_complaint_key(c) == domain for c in complaints)
                if not domain_in_complaints:
                    return False, f"Domain mismatch: question domain '{domain}' does not match complaint '{canonical_complaint}'."

        return True, "Valid"

    @classmethod
    def score_candidate(
        cls,
        question_dict: Dict[str, Any],
        state: Dict[str, Any],
        active_complaint: str,
        last_patient_utterance: Optional[str] = None
    ) -> float:
        """
        Calculates a clinical relevance score for ranking candidate questions.
        Higher score = higher priority and clinical appropriateness.
        """
        score = 0.0
        q_id = str(question_dict.get("id") or "").lower()
        q_text = str(question_dict.get("text") or question_dict.get("question") or "").lower()
        target_slot = str(question_dict.get("state_key") or question_dict.get("target_slot") or "").lower()
        canonical_complaint = cls.normalize_complaint_key(active_complaint)

        # 1. Base Priority Weight
        priority = question_dict.get("priority", "P2")
        if priority == "P0":
            score += 100.0  # Safety / Emergency
        elif priority == "P1":
            score += 70.0   # Essential HPI slot
        elif priority == "P2":
            score += 45.0   # Supporting details
        elif priority == "P3":
            score += 25.0   # Contextual
        else:
            score += 10.0

        # 2. Complaint Domain Match
        q_domain = str(question_dict.get("domain") or "").lower()
        if q_domain == canonical_complaint:
            score += 50.0
        elif q_domain == "generic":
            score += 15.0

        # 3. Missing High-Value Clinical Information Bonus
        hpi = state.get("hpi", {})
        if target_slot in ["onset", "duration", "duration_and_onset"] and not hpi.get("duration"):
            score += 35.0  # Duration is critical for triage
        elif target_slot in ["severity", "severity_and_onset"] and not hpi.get("severity"):
            score += 30.0  # Severity is essential
        elif target_slot in ["location", "location_and_radiation", "location_and_quadrant"] and not hpi.get("location"):
            score += 25.0
        elif target_slot == "character" and not hpi.get("character"):
            score += 20.0
        elif target_slot in ["triggers", "aggravating_and_relieving"] and not hpi.get("triggers"):
            score += 15.0

        # 4. Immediate Continuity Bonus with Patient's Most Recent Statement
        if last_patient_utterance:
            u_low = last_patient_utterance.lower()
            # If patient just mentioned a location, reward character / triggers
            if any(w in u_low for w in ["right", "left", "center", "front", "back", "side"]) and target_slot in ["character", "severity", "triggers"]:
                score += 20.0
            # If patient just mentioned a trigger (e.g. food, walking), reward relation to food/activity
            if any(w in u_low for w in ["eat", "food", "walk", "stairs", "touch", "light"]) and target_slot in ["triggers", "aggravating_and_relieving"]:
                score += 25.0

        return score

