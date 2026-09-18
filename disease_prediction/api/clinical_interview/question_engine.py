"""
MEDLENS AI — Clinical Question & Information Gap Engine (SIH PS 26047)
Transforms clinical case taking into an adaptive, conversational interview:
- Open-Ended First Question ("Please tell me in your own words what is bothering you today.")
- Information Gap Analyzer (Identifies what is already known and avoids redundant questions)
- Question Priority Hierarchy (P0 Red Flag > P1 Essential > P2 Supporting > P3 Contextual > P4 ROS)
- Multi-Complaint Merger (Fever + Cough + Weakness resolved into a single unified interview)
- Conversation Memory prefixing
- Maximum turns safety cap (12-14 questions max) and intelligent completion criteria
"""

from typing import Dict, Any, List, Optional
from .ontology import (
    CLINICAL_ONTOLOGY,
    GENERIC_CLINICAL_PATHWAY,
    SYSTEMIC_INQUIRY_MODULES,
    get_pathway_for_complaint,
    PRIORITY_P0,
    PRIORITY_P1,
    PRIORITY_P2,
    PRIORITY_P3,
    PRIORITY_P4
)
from .answer_extractor import ClinicalAnswerExtractor

class ClinicalQuestionEngine:
    """Selects the next prioritized, non-redundant clinical question based on the Information Gap."""

    def __init__(self):
        self.extractor = ClinicalAnswerExtractor()

    def get_first_open_ended_question(self, language_code: str = "en-IN") -> Dict[str, Any]:
        """Returns the canonical opening open-ended clinical prompt."""
        text_map = {
            "en-IN": "Please tell me in your own words what is bothering you today. What is your main problem?",
            "hi-IN": "कृपया अपने शब्दों में बताएं कि आज आपको क्या तकलीफ है? आपकी मुख्य समस्या क्या है?",
            "te-IN": "దయచేసి మీ మాటల్లో చెప్పండి, ఈరోజు మీకు ఏ ఇబ్బందిగా ఉంది? మీ ప్రధాన సమస్య ఏమిటి?",
            "or-IN": "ଦୟାକରି ଆପଣଙ୍କ ନିଜ ଭାଷାରେ କୁହନ୍ତୁ, ଆଜି ଆପଣଙ୍କୁ କି ଅସୁବିଧା ହେଉଛି? ଆପଣଙ୍କ ମୁଖ୍ୟ ସମସ୍ୟା କ'ଣ?",
            "ta-IN": "தயவுசெய்து உங்கள் சொந்த வார்த்தைகளில் கூறுங்கள், இன்று உங்களுக்கு என்ன பிரச்னை?"
        }

        return {
            "id": "chief_complaint_open",
            "question_id": "chief_complaint_open",
            "section": "Chief Complaint",
            "priority": PRIORITY_P1,
            "category": "chief_complaint",
            "text": text_map.get(language_code, text_map["en-IN"]),
            "question": text_map,
            "is_first_question": True,
            "quick_picks": [
                "Chest pain / సీన दर्द / ଛାତି ଯନ୍ତ୍ରଣା",
                "High fever & chills / बुखार / ଜ୍ୱର",
                "Severe headache / सिरदर्द / ମୁଣ୍ଡବିନ୍ଧା",
                "Stomach pain / पेट दर्द / ପେଟ ଯନ୍ତ୍ରଣା",
                "Shortness of breath / सांस फूलना",
                "Cough & cold / దగ్గు / କାଶ",
                "Joint / Knee pain / जोड़ों में दर्द",
                "General weakness / कमजोरी / ଦୁର୍ବଳତା"
            ],
            "allows_free_speech": True
        }

    def determine_next_question(self, state: Dict[str, Any], language_code: str = "en-IN") -> Optional[Dict[str, Any]]:
        """
        INFORMATION GAP ANALYZER & PRIORITY SELECTOR
        Examines state: What is already captured? What high-priority gap remains?
        Returns the single most important next question, or None if interview is complete.
        """
        # 1. Check if max turns limit reached
        asked_ids = set(state.get("asked_question_ids", []))
        turn_count = state.get("conversation_turn_count", 0)
        max_turns = state.get("max_turns_limit", 14)

        if turn_count >= max_turns:
            return None  # Safety cap reached

        # 2. Check if open-ended first question hasn't been asked yet
        if not state.get("chief_complaints") and "core.open_ended_complaint" not in asked_ids:
            return self.get_first_open_ended_question(language_code)

        # 3. Identify all active clinical pathways for all reported complaints (Multi-complaint merger)
        active_pathways: List[Dict[str, Any]] = []
        for complaint in state.get("chief_complaints", []):
            pw = get_pathway_for_complaint(complaint)
            if pw and pw not in active_pathways:
                active_pathways.append(pw)

        # 4. Build Candidate Question Queue with Information Gap Filtering
        candidate_questions: List[Dict[str, Any]] = []
        seen_state_keys = set()

        # A. Collect questions from specialized complaint pathways
        for pw in active_pathways:
            for q in pw.get("questions", []):
                q_id = q["id"]
                if q_id in asked_ids:
                    continue  # Already asked!

                # Information Gap Check: If information is already known, skip!
                state_key = q.get("state_key")
                if state_key:
                    if state_key in seen_state_keys:
                        continue  # Shared question already queued for earlier complaint
                    if self._is_parameter_already_known(state, state_key):
                        continue  # GAP IS ALREADY FILLED — DO NOT ASK AGAIN!
                    seen_state_keys.add(state_key)

                candidate_questions.append({
                    "raw_q": q,
                    "priority": q.get("priority", PRIORITY_P2),
                    "domain": pw.get("domain")
                })

        # B. If no specialized pathway matched, use Generic OPQRST
        if not active_pathways:
            for q in GENERIC_CLINICAL_PATHWAY:
                q_id = q["id"]
                if q_id in asked_ids:
                    continue
                state_key = q.get("state_key")
                if state_key:
                    if state_key in seen_state_keys:
                        continue
                    if self._is_parameter_already_known(state, state_key):
                        continue
                    seen_state_keys.add(state_key)

                candidate_questions.append({
                    "raw_q": q,
                    "priority": q.get("priority", PRIORITY_P2),
                    "domain": "generic"
                })

        # C. Include Systemic Contextual Inquiry (PMH, Meds, Allergies, Family, Social)
        # Only inject if we have already asked at least 1-2 HPI questions or turn_count >= 2
        if turn_count >= 2:
            if not state.get("past_medical_history") and "pmh.chronic_illnesses" not in asked_ids:
                q_pmh = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "pmh.chronic_illnesses"), None)
                if q_pmh: candidate_questions.append({"raw_q": q_pmh, "priority": PRIORITY_P2, "domain": "past_medical"})

            if not state.get("medications") and "med.current_reconciliation" not in asked_ids:
                q_med = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "med.current_reconciliation"), None)
                if q_med: candidate_questions.append({"raw_q": q_med, "priority": PRIORITY_P2, "domain": "medications"})

            if not state.get("allergies") and "allergy.drug_reactions" not in asked_ids:
                q_all = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "allergy.drug_reactions"), None)
                if q_all: candidate_questions.append({"raw_q": q_all, "priority": PRIORITY_P2, "domain": "allergies"})

            if not state.get("family_history") and "fh.hereditary" not in asked_ids and turn_count >= 5:
                q_fh = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "fh.hereditary"), None)
                if q_fh: candidate_questions.append({"raw_q": q_fh, "priority": PRIORITY_P3, "domain": "family_history"})

        if not candidate_questions:
            return None  # All gaps filled, no questions pending!

        # 5. Sort candidate questions strictly by Priority Hierarchy
        priority_weights = {
            PRIORITY_P0: 0,
            PRIORITY_P1: 1,
            PRIORITY_P2: 2,
            PRIORITY_P3: 3,
            PRIORITY_P4: 4
        }
        candidate_questions.sort(key=lambda item: priority_weights.get(item["priority"], 99))

        # Pick the top priority question
        chosen = candidate_questions[0]["raw_q"]
        chosen_id = chosen["id"]

        # 6. Apply Conversation Memory Context
        memory_prefix = self.extractor.build_contextual_conversation_prefix(state, chosen_id, language_code)
        raw_text_dict = chosen.get("text", {})
        localized_text = raw_text_dict.get(language_code) or raw_text_dict.get("en-IN") or ""
        final_text = f"{memory_prefix}{localized_text}"

        raw_translations = {}
        if raw_text_dict:
            for l_code, l_txt in raw_text_dict.items():
                raw_translations[l_code] = f"{memory_prefix}{l_txt}"
        else:
            raw_translations["en-IN"] = final_text

        section_name = chosen.get("section") or chosen.get("category") or candidate_questions[0]["domain"].replace("_", " ").title()

        return {
            "id": chosen_id,
            "question_id": chosen_id,
            "section": section_name,
            "priority": chosen.get("priority", PRIORITY_P2),
            "state_key": chosen.get("state_key"),
            "text": final_text,
            "question": raw_translations,
            "raw_q": chosen,
            "quick_picks": chosen.get("quick_picks", []),
            "red_flag_triggers": chosen.get("red_flag_triggers", []),
            "domain": candidate_questions[0]["domain"]
        }

    def _is_parameter_already_known(self, state_or_hpi: Dict[str, Any], state_key: str) -> bool:
        """
        Checks if the requested clinical parameter has already been captured
        during the opening statement or previous responses.
        Uses get_parameter_value to safely unpack dictionaries or primitives.
        """
        from .state_manager import get_parameter_value
        wrapper = state_or_hpi if "hpi" in state_or_hpi else {"hpi": state_or_hpi}

        def has_val(k):
            v = get_parameter_value(wrapper, k)
            return v is not None and str(v).strip() != "" and str(v).strip().lower() != "none"

        if state_key == "location_and_radiation":
            return has_val("location") and has_val("radiation")
        elif state_key in ["duration_and_onset", "duration"]:
            return has_val("duration")
        elif state_key in ["severity_and_onset", "severity"]:
            return has_val("severity")
        elif state_key == "character":
            return has_val("character")
        elif state_key == "exertional_relationship":
            return has_val("exertional_relationship")
        elif state_key in ["associated_symptoms", "associated"]:
            assoc = get_parameter_value(wrapper, "associated_symptoms")
            return bool(assoc)
        else:
            return has_val(state_key)

    @classmethod
    def generate_open_ended_first_question(cls, language_code: str = "en-IN") -> Dict[str, Any]:
        engine = cls()
        res = engine.get_first_open_ended_question(language_code)
        res["id"] = res.get("question_id", "core.open_ended_complaint")
        res["parameter"] = "chief_complaint"
        res["question"] = {
            "en-IN": "Please tell me in your own words what is bothering you today. What is your main problem?",
            "hi-IN": "कृपया अपने शब्दों में बताएं कि आज आपको क्या तकलीफ है? आपकी मुख्य समस्या क्या है?",
            "te-IN": "దయచేసి మీ మాటల్లో చెప్పండి, ఈరోజు మీకు ఏ ఇబ్బందిగా ఉంది? మీ ప్రధాన సమస్య ఏమిటి?",
            "or-IN": "ଦୟାକରି ଆପଣଙ୍କ ନିଜ ଭାଷାରେ କୁହନ୍ତୁ, ଆଜି ଆପଣଙ୍କୁ କି ଅସୁବିଧା ହେଉଛି? ଆପଣଙ୍କ ମୁଖ୍ୟ ସମସ୍ୟା କ'ଣ?",
            "ta-IN": "தயவுசெய்து உங்கள் சொந்த வார்த்தைகளில் கூறுங்கள், இன்று உங்களுக்கு என்ன பிரச்னை?"
        }
        return res

    @classmethod
    def select_next_question(
        cls,
        patient_state: Dict[str, Any],
        current_language: str = "en-IN",
        last_answer_entities: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        engine = cls()
        # Support both chief_complaint and chief_complaints in state
        if not patient_state.get("chief_complaints") and patient_state.get("chief_complaint"):
            patient_state["chief_complaints"] = [patient_state["chief_complaint"]]

        q = engine.determine_next_question(patient_state, current_language)
        if not q:
            return None

        raw = q.get("raw_q", q)
        q_id = raw.get("id", raw.get("question_id", "q_next"))

        raw_text_dict = raw.get("text", {})
        if isinstance(raw_text_dict, dict) and raw_text_dict:
            translations = {}
            for l_code, l_text in raw_text_dict.items():
                pfx = engine.extractor.build_contextual_conversation_prefix(patient_state, q_id, l_code)
                translations[l_code] = f"{pfx}{l_text}"
        elif isinstance(q.get("text"), str):
            translations = {current_language: q["text"], "en-IN": q["text"]}
        else:
            translations = raw.get("translations", raw.get("text_map", {current_language: "", "en-IN": ""}))

        return {
            "id": q_id,
            "parameter": raw.get("state_key", raw.get("parameter", "general")),
            "priority": raw.get("priority", PRIORITY_P1),
            "question": translations,
            "quick_picks": q.get("quick_picks", raw.get("quick_picks", []))
        }

