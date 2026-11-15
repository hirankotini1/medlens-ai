"""
MEDLENS AI — Clinical Question & Information Gap Engine (SIH PS 26047)
Transforms clinical case taking into an adaptive, conversational interview:
- Open-Ended First Question ("Please tell me in your own words what is bothering you today.")
- Ambiguity Detection & Clarification Dispatcher
- Information Gap Analyzer (Identifies what is already known and avoids redundant questions)
- Strict Cross-System Jump Prohibition & Relevance Validation
- Clinical Relevance Scoring & Priority Ordering
- Multi-Complaint Merger (Fever + Headache + Body aches resolved in a coherent cluster)
- Conversation Memory prefixing
- Maximum turns safety cap (14-16 questions max) and intelligent completion criteria
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from .ontology import (
    CLINICAL_ONTOLOGY,
    GENERIC_CLINICAL_PATHWAY,
    SYSTEMIC_INQUIRY_MODULES,
    AYURVEDA_PATHWAY,
    HOMEOPATHY_PATHWAY,
    get_pathway_for_complaint,
    get_generic_pathway,
    get_ayurveda_pathway,
    get_homeopathy_pathway,
    PRIORITY_P0,
    PRIORITY_P1,
    PRIORITY_P2,
    PRIORITY_P3,
    PRIORITY_P4
)
from .answer_extractor import ClinicalAnswerExtractor
from .relevance_validator import ClinicalQuestionRelevanceValidator

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
                "Chest pain / सीने में दर्द / ଛାତି ଯନ୍ତ୍ରଣା",
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
        INFORMATION GAP ANALYZER & CLINICAL RELEVANCE SELECTOR
        Examines state: What is already captured? What high-priority gap remains?
        Returns the single most important next question, or None if interview is complete.
        """
        # 1. Check if max patient answers limit reached
        asked_ids = set(state.get("asked_question_ids", []))
        patient_answers = state.get("patient_answer_count", 0)
        max_answers = state.get("max_patient_answers", 16)

        if patient_answers >= max_answers:
            return None  # Safety cap reached

        # 2. Check if open-ended first question hasn't been asked yet
        if not state.get("chief_complaints") and "chief_complaint_open" not in asked_ids:
            return self.get_first_open_ended_question(language_code)

        # 2b. Check for Ambiguous / Non-specific patient complaint
        complaints = state.get("chief_complaints", [])
        raw_complaint = state.get("raw_complaints_text") or (complaints[0] if complaints else "")
        if ClinicalQuestionRelevanceValidator.is_ambiguous_complaint(raw_complaint):
            if "clarify_chief_complaint" not in asked_ids:
                return ClinicalQuestionRelevanceValidator.get_clarification_question(language_code)

        # Get last patient statement for recency and continuity scoring
        transcript = state.get("conversation_transcript", [])
        patient_turns = [t.get("text") for t in transcript if t.get("speaker") == "patient" and t.get("text")]
        last_patient_stmt = patient_turns[-1] if patient_turns else ""

        candidate_questions: List[Dict[str, Any]] = []
        seen_state_keys = set()
        case_type = state.get("case_type", "general")

        # 3. ROUTE ACCORDING TO AUTHORITATIVE CASE TYPE (General / Ayurveda / Homeopathy)
        if case_type == "ayurveda":
            # --- AYURVEDA CLINICAL PATHWAY ---
            if not self._is_parameter_already_known(state, "duration"):
                q_dur = next((q for q in GENERIC_CLINICAL_PATHWAY if q.get("state_key") == "duration_and_onset"), None)
                if q_dur and q_dur["id"] not in asked_ids:
                    candidate_questions.append({
                        "raw_q": q_dur,
                        "priority": PRIORITY_P1,
                        "domain": "ayurveda_hpi",
                        "score": 85.0
                    })
                    seen_state_keys.add("duration")

            all_complaints_text = " ".join(state.get("chief_complaints", [])).lower()
            is_digestive = any(w in all_complaints_text for w in ["digest", "stomach", "acidity", "gas", "constipat", "appetite", "motion", "loose", "vomit", "purg"])

            for q in AYURVEDA_PATHWAY:
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

                q_priority = q.get("priority", PRIORITY_P2)
                score = 60.0
                if is_digestive and q.get("state_key") in ["agni", "koshtha", "ahara"]:
                    q_priority = PRIORITY_P1
                    score = 90.0

                candidate_questions.append({
                    "raw_q": q,
                    "priority": q_priority,
                    "domain": "ayurveda",
                    "score": score
                })

            if patient_answers >= 2:
                if not state.get("medications") and "med.current_reconciliation" not in asked_ids:
                    q_med = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "med.current_reconciliation"), None)
                    if q_med: candidate_questions.append({"raw_q": q_med, "priority": PRIORITY_P2, "domain": "medications", "score": 40.0})
                if not state.get("allergies") and "allergy.drug_reactions" not in asked_ids:
                    q_all = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "allergy.drug_reactions"), None)
                    if q_all: candidate_questions.append({"raw_q": q_all, "priority": PRIORITY_P2, "domain": "allergies", "score": 40.0})

        elif case_type == "homeopathy":
            # --- HOMEOPATHY CLINICAL PATHWAY ---
            if not self._is_parameter_already_known(state, "duration"):
                q_dur = next((q for q in GENERIC_CLINICAL_PATHWAY if q.get("state_key") == "duration_and_onset"), None)
                if q_dur and q_dur["id"] not in asked_ids:
                    candidate_questions.append({
                        "raw_q": q_dur,
                        "priority": PRIORITY_P1,
                        "domain": "homeopathy_hpi",
                        "score": 85.0
                    })
                    seen_state_keys.add("duration")

            for q in HOMEOPATHY_PATHWAY:
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
                    "domain": "homeopathy",
                    "score": 65.0
                })

            if patient_answers >= 2:
                if not state.get("past_medical_history") and "pmh.chronic_illnesses" not in asked_ids:
                    q_pmh = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "pmh.chronic_illnesses"), None)
                    if q_pmh: candidate_questions.append({"raw_q": q_pmh, "priority": PRIORITY_P2, "domain": "past_medical", "score": 40.0})
                if not state.get("allergies") and "allergy.drug_reactions" not in asked_ids:
                    q_all = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "allergy.drug_reactions"), None)
                    if q_all: candidate_questions.append({"raw_q": q_all, "priority": PRIORITY_P2, "domain": "allergies", "score": 40.0})

        else:
            # --- GENERAL CLINICAL PATHWAY ---
            # Identify active clinical pathways for all reported complaints (Multi-complaint merger)
            active_pathways: List[Dict[str, Any]] = []
            for complaint in complaints:
                pw = get_pathway_for_complaint(complaint)
                if pw and pw not in active_pathways:
                    active_pathways.append(pw)

            # A. Collect questions from specialized complaint pathways with strict validation & scoring
            for pw in active_pathways:
                pw_domain = pw.get("domain", "")
                for q in pw.get("questions", []):
                    q_id = q["id"]
                    if q_id in asked_ids:
                        continue

                    state_key = q.get("state_key")
                    if state_key:
                        if state_key in seen_state_keys:
                            continue
                        if self._is_parameter_already_known(state, state_key):
                            continue

                    # Validate question relevance & cross-system jump prohibition
                    is_valid, rej_reason = ClinicalQuestionRelevanceValidator.validate_question(
                        q, state, active_complaint=pw_domain
                    )
                    if not is_valid:
                        continue

                    if state_key:
                        seen_state_keys.add(state_key)

                    score = ClinicalQuestionRelevanceValidator.score_candidate(
                        question_dict=q,
                        state=state,
                        active_complaint=pw_domain,
                        last_patient_utterance=last_patient_stmt
                    )

                    candidate_questions.append({
                        "raw_q": q,
                        "priority": q.get("priority", PRIORITY_P2),
                        "domain": pw_domain,
                        "score": score
                    })

            # B. If no specialized pathway matched, use Generic OPQRST with strict validation
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

                    is_valid, rej_reason = ClinicalQuestionRelevanceValidator.validate_question(
                        q, state, active_complaint="generic"
                    )
                    if not is_valid:
                        continue

                    seen_state_keys.add(state_key)
                    score = ClinicalQuestionRelevanceValidator.score_candidate(
                        question_dict=q,
                        state=state,
                        active_complaint="generic",
                        last_patient_utterance=last_patient_stmt
                    )

                    candidate_questions.append({
                        "raw_q": q,
                        "priority": q.get("priority", PRIORITY_P2),
                        "domain": "generic",
                        "score": score
                    })

            # C. Systemic Contextual Inquiry (PMH, Meds, Allergies, Family)
            # Only introduced after core HPI is established (at least 2-3 patient answers)
            if patient_answers >= 3:
                if not state.get("past_medical_history") and "pmh.chronic_illnesses" not in asked_ids:
                    q_pmh = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "pmh.chronic_illnesses"), None)
                    if q_pmh: candidate_questions.append({"raw_q": q_pmh, "priority": PRIORITY_P2, "domain": "past_medical", "score": 35.0})

                if not state.get("medications") and "med.current_reconciliation" not in asked_ids:
                    q_med = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "med.current_reconciliation"), None)
                    if q_med: candidate_questions.append({"raw_q": q_med, "priority": PRIORITY_P2, "domain": "medications", "score": 35.0})

                if not state.get("allergies") and "allergy.drug_reactions" not in asked_ids:
                    q_all = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "allergy.drug_reactions"), None)
                    if q_all: candidate_questions.append({"raw_q": q_all, "priority": PRIORITY_P2, "domain": "allergies", "score": 35.0})

                if not state.get("family_history") and "fh.hereditary" not in asked_ids and patient_answers >= 6:
                    q_fh = next((m for m in SYSTEMIC_INQUIRY_MODULES if m["id"] == "fh.hereditary"), None)
                    if q_fh: candidate_questions.append({"raw_q": q_fh, "priority": PRIORITY_P3, "domain": "family_history", "score": 20.0})

        if not candidate_questions:
            return None  # All clinical information gaps resolved!

        # 4. Sort candidate questions strictly by clinical relevance score descending
        candidate_questions.sort(key=lambda item: item["score"], reverse=True)

        # Pick the top priority, validated question
        chosen = candidate_questions[0]["raw_q"]
        chosen_id = chosen["id"]
        chosen_domain = candidate_questions[0]["domain"]

        # 5. Apply Conversation Memory Context
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

        # 6. Dynamic AI Rephraser with strict safety & relevance validation
        ai_res = self._attempt_ai_rephrase(chosen, state, final_text, language_code)
        if ai_res and ai_res.get("text"):
            ai_cand_dict = {
                "id": chosen_id,
                "text": ai_res["text"],
                "target_slot": chosen.get("state_key"),
                "domain": chosen_domain
            }
            is_ai_valid, ai_rej = ClinicalQuestionRelevanceValidator.validate_question(
                ai_cand_dict, state, active_complaint=chosen_domain
            )
            if is_ai_valid:
                final_text = ai_res["text"]
                raw_translations[language_code] = final_text
                if ai_res.get("quick_picks") and len(ai_res["quick_picks"]) >= 2:
                    chosen_picks = ai_res["quick_picks"]
            else:
                logging.getLogger("clinical_interview").warning(
                    f"Discarded off-target AI question rephrase: {ai_rej}. Retaining clinical question."
                )

        section_name = chosen.get("section") or chosen.get("category") or chosen_domain.replace("_", " ").title()
        why_asking_text = chosen.get("why_asking") or "This question helps complete your clinical case history for physician evaluation."

        return {
            "id": chosen_id,
            "question_id": chosen_id,
            "section": section_name,
            "priority": chosen.get("priority", PRIORITY_P2),
            "state_key": chosen.get("state_key"),
            "why_asking": why_asking_text,
            "text": final_text,
            "question": raw_translations,
            "raw_q": chosen,
            "quick_picks": chosen_picks,
            "red_flag_triggers": chosen.get("red_flag_triggers", []),
            "domain": chosen_domain,
            "is_followup": True
        }

    def _attempt_ai_rephrase(self, chosen: Dict[str, Any], state: Dict[str, Any], base_text: str, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to use OpenRouter AI API to rephrase the question naturally based on
        the patient's exact previous utterance, with a fast timeout.
        Returns dict with 'text' and 'quick_picks' or None on timeout/error.
        """
        try:
            from disease_prediction.api.openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME, is_circuit_open, trip_circuit_breaker
            import requests

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
                f"2. Stay strictly on the topic of '{primary_complaint}'. Do NOT introduce other body systems (no breathing questions for headache, no arm pain for stomach pain).\n"
                f"3. Provide 3 to 4 concise quick-pick answer choices in the same language.\n"
                f"4. Strict rule: DO NOT diagnose, advise, or prescribe.\n"
                f"5. Output ONLY the raw JSON object. No reasoning or markdown.\n\n"
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
                            {"role": "system", "content": "You are a clinical inquiry rephraser. Return ONLY valid JSON with question and quick_picks. Stay strictly on topic."},
                            {"role": "user", "content": prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2,
                        "max_tokens": 300
                    }
                    resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=(1.5, 4.0))
                    if resp.status_code == 200:
                        choice = resp.json().get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        raw_c = (msg.get("content") or msg.get("reasoning") or "").strip()
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
                        trip_circuit_breaker(180.0, "OpenRouter daily quota limit reached")
                        return None
                except Exception as e:
                    logging.getLogger("clinical_interview").warning(f"AI Rephrase attempt failed on {model_name}: {e}")
                    continue
        except Exception as e:
            logging.getLogger("clinical_interview").warning(f"AI Rephrase outer error: {e}")
        return None

    def _is_parameter_already_known(self, state_or_hpi: Dict[str, Any], state_key: str) -> bool:
        """
        Checks if the requested clinical parameter has already been captured
        or skipped/marked unknown during the interview.
        Uses get_parameter_value to safely unpack dictionaries or primitives.
        """
        from .state_manager import get_parameter_value
        wrapper = state_or_hpi if "hpi" in state_or_hpi else {"hpi": state_or_hpi}

        # If parameter has been recorded in information_gaps as skipped/unknown, do not re-ask
        for gap in wrapper.get("information_gaps", []):
            gap_param = gap.get("parameter") if isinstance(gap, dict) else str(gap)
            if gap_param and gap_param.lower() == str(state_key).lower():
                return True

        def has_val(k):
            v = get_parameter_value(wrapper, k)
            if v is not None and str(v).strip() != "" and str(v).strip().lower() not in ["none", "null", "undefined"]:
                return True
            ayush = wrapper.get("ayush_parameters", {})
            if isinstance(ayush, dict):
                v_ayush = ayush.get(k)
                if isinstance(v_ayush, dict):
                    v_ayush = v_ayush.get("value")
                if v_ayush is not None and str(v_ayush).strip() != "":
                    return True
                dasha = ayush.get("dashavidha_pariksha", {})
                if isinstance(dasha, dict):
                    v_d = dasha.get(k)
                    if isinstance(v_d, dict):
                        v_d = v_d.get("value")
                    if v_d is not None and str(v_d).strip() != "":
                        return True
            homeo = wrapper.get("homeopathy_parameters", {})
            if isinstance(homeo, dict):
                v_h = homeo.get(k)
                if isinstance(v_h, dict):
                    v_h = v_h.get("value")
                if v_h is not None and str(v_h).strip() != "":
                    return True
            return False

        if state_key in ["location_and_radiation", "location"]:
            return has_val("location")
        elif state_key in ["duration_and_onset", "duration"]:
            return has_val("duration")
        elif state_key in ["severity_and_onset", "severity"]:
            return has_val("severity")
        elif state_key in ["character", "character_and_quality"]:
            return has_val("character")
        elif state_key in ["exertional_relationship", "triggers", "aggravating_and_relieving"]:
            return has_val("exertional_relationship") or has_val("triggers") or has_val("aggravating_and_relieving")
        elif state_key in ["associated_symptoms", "associated"]:
            assoc = get_parameter_value(wrapper, "associated_symptoms")
            return bool(assoc)
        elif state_key in ["thermal_and_thirst", "thermal_preference"]:
            return has_val("thermal_preference") or has_val("thermal_and_thirst")
        else:
            return has_val(state_key)

    @classmethod
    def generate_open_ended_first_question(cls, language_code: str = "en-IN") -> Dict[str, Any]:
        engine = cls()
        res = engine.get_first_open_ended_question(language_code)
        res["id"] = "chief_complaint_open"
        res["question_id"] = "chief_complaint_open"
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
        if not patient_state.get("chief_complaints") and patient_state.get("chief_complaint"):
            patient_state["chief_complaints"] = [patient_state["chief_complaint"]]

        q = engine.determine_next_question(patient_state, current_language)
        if not q:
            return None

        raw = q.get("raw_q", q)
        q_id = raw.get("id", raw.get("question_id", "q_next"))

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

        raw_picks = q.get("quick_picks") or raw.get("quick_picks", [])
        clean_picks = [str(p).replace("\ufffd", "-").strip() for p in raw_picks if str(p).strip()]

        final_question_text = q.get("text") or translations.get(current_language) or translations.get("en-IN") or ""

        return {
            "id": q_id,
            "parameter": raw.get("state_key", raw.get("parameter", "general")),
            "priority": raw.get("priority", PRIORITY_P1),
            "why_asking": q.get("why_asking") or raw.get("why_asking") or "This question helps complete your clinical case history for physician evaluation.",
            "text": final_question_text,
            "question": translations,
            "quick_picks": clean_picks
        }
