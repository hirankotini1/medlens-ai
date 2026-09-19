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

import os
import logging
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
                pfx = self.extractor.build_contextual_conversation_prefix(state, chosen_id, l_code)
                raw_translations[l_code] = f"{pfx}{l_txt}"
        else:
            raw_translations["en-IN"] = final_text

        chosen_picks = chosen.get("quick_picks", [])

        # 7. Dynamic AI Rephraser (Augments question with deep context if online)
        ai_res = self._attempt_ai_rephrase(chosen, state, final_text, language_code)
        if ai_res and ai_res.get("text"):
            final_text = ai_res["text"]
            raw_translations[language_code] = final_text
            if ai_res.get("quick_picks") and len(ai_res["quick_picks"]) >= 2:
                chosen_picks = ai_res["quick_picks"]

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
            "quick_picks": chosen_picks,
            "red_flag_triggers": chosen.get("red_flag_triggers", []),
            "domain": candidate_questions[0]["domain"],
            "is_followup": True
        }

    def _attempt_ai_rephrase(self, chosen: Dict[str, Any], state: Dict[str, Any], base_text: str, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to use OpenRouter AI API to rephrase the question naturally based on
        the patient's exact previous utterance, with a fast timeout.
        Returns dict with "text" and "quick_picks" or None on timeout/error.
        """
        try:
            from disease_prediction.api.openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME, is_circuit_open, trip_circuit_breaker
            import requests
            import json
            import re

            if is_circuit_open():
                return None
            
            api_key = get_api_key()
            if not api_key:
                return None

            transcript = state.get("conversation_transcript", [])
            patient_turns = [t.get("text") for t in transcript if t.get("speaker") == "patient" and t.get("text")]
            last_stmt = patient_turns[-1] if patient_turns else ""
            if not last_stmt or len(last_stmt.strip()) < 3:
                return None

            complaints = state.get("chief_complaints", [])
            primary_complaint = complaints[0] if complaints else "symptoms"

            candidate_models = [
                os.getenv("OPENROUTER_FOLLOWUP_MODEL", "nex-agi/nex-n2.5-mini:free"),
                "openrouter/free"
            ]

            prompt = (
                f"You are an empathetic, highly skilled doctor/nurse taking patient history in an outpatient hospital clinic.\n"
                f"Patient's recent statement: \"{last_stmt}\"\n"
                f"Reported complaint: \"{primary_complaint}\"\n"
                f"Clinical objective you need to ask: \"{base_text}\"\n"
                f"Target Language: {language_code}\n\n"
                f"Instructions:\n"
                f"1. Acknowledge what the patient shared with clinical empathy and warmth, and smoothly ask the clinical objective in {language_code}.\n"
                f"2. Provide 3 to 4 concise quick-pick answer choices in the same language.\n"
                f"3. Strict rule: DO NOT diagnose, advise, or prescribe.\n"
                f"4. Do NOT output thought/reasoning text. Output ONLY the raw JSON object.\n\n"
                f'{{"question": "Warm empathetic question here", "quick_picks": ["Option 1", "Option 2", "Option 3"]}}'
            )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": SITE_URL,
                "X-Title": APP_NAME,
                "Content-Type": "application/json"
            }

            for model_name in candidate_models:
                try:
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": "You are a clinical inquiry rephraser. Return ONLY the JSON object. No reasoning or thoughts."},
                            {"role": "user", "content": prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2,
                        "max_tokens": 300
                    }
                    resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=(1.5, 4.5))
                    if resp.status_code == 200:
                        choice = resp.json().get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        raw_c = (msg.get("content") or msg.get("reasoning") or "").strip()
                        # Clean common quote encoding glitches
                        raw_c = raw_c.replace("\ufffd", "-").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
                        m = re.search(r'(\{[\s\S]*\})', raw_c)
                        if m:
                            parsed = json.loads(m.group(1))
                            q_txt = str(parsed.get("question") or "").strip()
                            if q_txt and len(q_txt) > 8 and "..." not in q_txt and "Warm empathetic question" not in q_txt:
                                q_picks = [str(x).strip().replace("\ufffd", "-") for x in parsed.get("quick_picks", []) if str(x).strip() and "Option" not in str(x)][:4]
                                return {
                                    "text": q_txt,
                                    "quick_picks": q_picks if len(q_picks) >= 2 else (chosen.get("quick_picks") or [])
                                }
                    elif resp.status_code == 429:
                        trip_circuit_breaker(180.0, "OpenRouter daily quota limit reached (50/50)")
                        return None
                except Exception as e:
                    import logging

                    logging.getLogger("clinical_interview").warning(f"AI Rephrase attempt failed on {model_name}: {e}")
                    continue
        except Exception as e:
            import logging
            logging.getLogger("clinical_interview").warning(f"AI Rephrase outer error: {e}")
        return None

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

        # Check if q already has valid translations (including AI rephrased text)
        if q.get("question") and isinstance(q["question"], dict) and q["question"]:

            translations = dict(q["question"])
        elif isinstance(q.get("text"), str) and q.get("text"):
            translations = {current_language: q["text"], "en-IN": q["text"]}
        else:
            raw_text_dict = raw.get("text", {})
            if isinstance(raw_text_dict, dict) and raw_text_dict:
                translations = {}
                for l_code, l_text in raw_text_dict.items():
                    pfx = engine.extractor.build_contextual_conversation_prefix(patient_state, q_id, l_code)
                    translations[l_code] = f"{pfx}{l_text}"
            else:
                translations = raw.get("translations", raw.get("text_map", {current_language: "", "en-IN": ""}))

        # Clean unicode artifacts (\ufffd) in quick_picks
        raw_picks = q.get("quick_picks") or raw.get("quick_picks", [])
        clean_picks = [str(p).replace("\ufffd", "-").strip() for p in raw_picks if str(p).strip()]

        final_question_text = q.get("text") or translations.get(current_language) or translations.get("en-IN") or ""

        return {
            "id": q_id,
            "parameter": raw.get("state_key", raw.get("parameter", "general")),
            "priority": raw.get("priority", PRIORITY_P1),
            "text": final_question_text,
            "question": translations,
            "quick_picks": clean_picks
        }


