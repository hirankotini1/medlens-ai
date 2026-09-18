"""
MEDLENS AI — Clinical Patient State Manager (SIH PS 26047)
Maintains the complete structured case state across the conversational interview:
- Demographics
- Chief Complaints (multi-complaint support)
- History of Present Illness (HPI structured parameters)
- Past Medical & Surgical History
- Current Medications & Adherence
- Allergies & Reactions
- Family History & Hereditary Risks
- Personal, Social & Occupational History
- Review of Systems (ROS)
- Attached Documents & OCR Parameters
- Red Flags & Urgent Triage Events
- Contradictions & Discrepancies
- Uncertainties Needing Physician Review
- Source Provenance Log & Medical Timeline
- Privacy & Demo Mode Guards
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

def create_initial_patient_state(
    patient_id: str,
    language_code: str = "en-IN",
    case_id: Optional[str] = None,
    primary_language: Optional[str] = None,
    abha_id: Optional[str] = None,
    demographics: Optional[Dict[str, Any]] = None,
    is_demo_mode: bool = False,
    is_kiosk: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Initializes a blank, structured clinical interview state."""
    demo_dict = demographics or {}
    lang = primary_language or language_code or "en-IN"
    c_id = case_id or f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    clean_demographics = {
        "name": demo_dict.get("name", "Outpatient"),
        "age": demo_dict.get("age", "—"),
        "gender": demo_dict.get("gender", "—"),
        "contact": demo_dict.get("contact", "—"),
        "is_demo_mode": is_demo_mode
    }

    return {
        "session_id": f"INTERVIEW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "case_id": c_id,
        "patient_id": patient_id,
        "abha_id": abha_id or "",
        "language": lang,
        "primary_language": lang,
        "is_demo_mode": is_demo_mode,
        "is_kiosk": is_kiosk,
        "interview_started_at": datetime.now(timezone.utc).isoformat(),
        "interview_status": "in_progress",
        "triage_urgency": "ROUTINE",

        # Clinical Core State
        "chief_complaint": "",
        "chief_complaints": [],
        "raw_complaints_text": "",
        "hpi": {
            "onset": None,
            "duration": None,
            "location": None,
            "character": None,
            "severity": None,
            "radiation": None,
            "timing": None,
            "exertional_relationship": None,
            "positional_relationship": None,
            "aggravating_factors": [],
            "relieving_factors": [],
            "associated_symptoms": [],
            "triggers": None,
            "relievers": None
        },
        "past_medical_history": [],
        "past_surgical_history": [],
        "medications": [],
        "allergies": [],
        "family_history": [],
        "personal_social_history": {
            "occupation": None,
            "tobacco": None,
            "smoking": None,
            "alcohol": None,
            "diet": None,
            "physical_activity": None
        },
        "review_of_systems": {},
        "ayush_parameters": {},

        # Safety & Triage State
        "red_flags": [],
        "red_flags_detected": [],
        "active_red_flag_alert": None,
        "is_red_flag_paused": False,
        "contradictions": [],
        "uncertainties": [],
        "completed_domains": [],

        # Provenance & Transcripts
        "documents": [],
        "timeline": [],
        "source_provenance": [],
        "provenance_log": [],
        "conversation_history": [],
        "conversation_turn_count": 0,
        "max_turns_limit": 14,
        "asked_question_ids": []
    }


class PatientStateManager:
    """Manages mutations, consistency checks, and persistence for patient interview state."""

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or create_initial_patient_state("PAT-UNKNOWN")

    @classmethod
    def update_hpi_parameter(
        cls,
        state: Dict[str, Any],
        parameter_name: str,
        value: Any,
        source: str = "patient_voice",
        confidence: float = 0.85,
        raw_text: str = ""
    ) -> Dict[str, Any]:
        """Updates an HPI parameter with value, source, confidence and logs provenance."""
        if not isinstance(state.get("hpi"), dict):
            state["hpi"] = {}

        state["hpi"][parameter_name] = {
            "value": value,
            "source": source,
            "confidence": confidence,
            "raw_text": raw_text
        }

        # Also mirror in plain keys if medications or allergies for direct access
        if parameter_name == "medications":
            state["medications_queried"] = True
            if isinstance(value, list):
                state["medications"] = value
            elif isinstance(value, str):
                state["medications"] = [value]
        elif parameter_name == "allergies":
            state["allergies_queried"] = True
            if isinstance(value, list):
                state["allergies"] = value
            elif isinstance(value, str):
                state["allergies"] = [value]

        if "source_provenance" not in state:
            state["source_provenance"] = []
        state["source_provenance"].append({
            "parameter": f"hpi.{parameter_name}",
            "value": value,
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return state

    @classmethod
    def set_chief_complaint(cls, state: Dict[str, Any], complaint: str, source: str = "patient_voice") -> Dict[str, Any]:
        state["chief_complaint"] = complaint
        if "chief_complaints" not in state:
            state["chief_complaints"] = []
        if complaint not in state["chief_complaints"]:
            state["chief_complaints"].append(complaint)
        return state

    @classmethod
    def add_red_flag(cls, state: Dict[str, Any], red_flag_data: Dict[str, Any]) -> Dict[str, Any]:
        if "red_flags_detected" not in state:
            state["red_flags_detected"] = []
        state["red_flags_detected"].append(red_flag_data)
        state["triage_urgency"] = red_flag_data.get("urgency", "CRITICAL")
        state["interview_status"] = "paused_red_flag"
        state["is_red_flag_paused"] = True
        return state

    @classmethod
    def add_contradiction(cls, state: Dict[str, Any], contra: Dict[str, Any]) -> Dict[str, Any]:
        if "contradictions" not in state:
            state["contradictions"] = []
        state["contradictions"].append(contra)
        return state

    @classmethod
    def add_uncertainty(cls, state: Dict[str, Any], uncertainty: Dict[str, Any]) -> Dict[str, Any]:
        if "uncertainties" not in state:
            state["uncertainties"] = []
        state["uncertainties"].append(uncertainty)
        return state

    @classmethod
    def correct_fact(cls, state: Dict[str, Any], parameter_name: str, new_value: Any, corrected_by: str = "patient", reason: str = "") -> Dict[str, Any]:
        if not isinstance(state.get("hpi"), dict):
            state["hpi"] = {}
        old_val = state["hpi"].get(parameter_name, {}).get("value") if isinstance(state["hpi"].get(parameter_name), dict) else state["hpi"].get(parameter_name)
        state["hpi"][parameter_name] = {
            "value": new_value,
            "source": f"corrected_by_{corrected_by}",
            "confidence": 1.0,
            "corrected_from": old_val
        }
        if "provenance_log" not in state:
            state["provenance_log"] = []
        state["provenance_log"].append({
            "action": "correction",
            "parameter": parameter_name,
            "old_value": old_val,
            "new_value": new_value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return state

    @classmethod
    def append_conversation_turn(
        cls,
        state: Dict[str, Any],
        speaker: str,
        text: str,
        language: str = "en-IN",
        audio_confidence: float = 1.0,
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if "conversation_history" not in state:
            state["conversation_history"] = []
        state["conversation_history"].append({
            "turn_index": len(state["conversation_history"]) + 1,
            "speaker": speaker,
            "text": text,
            "language": language,
            "audio_confidence": audio_confidence,
            "extracted_entities": extracted_entities or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        state["conversation_turn_count"] = state.get("conversation_turn_count", 0) + 1
        return state

    @classmethod
    def sanitize_for_export(cls, state: Dict[str, Any], is_physician_view: bool = False) -> Dict[str, Any]:
        clean = dict(state)
        clean.pop("password_hash", None)
        if not is_physician_view:
            clean.pop("access_pin", None)
            clean.pop("access_pin_hash", None)
        return clean

    # Instance methods for OOP usage
    def get_state(self) -> Dict[str, Any]:
        return self.state
