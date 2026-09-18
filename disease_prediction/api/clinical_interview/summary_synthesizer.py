"""
MedLens Clinical Interview Engine — Clinical Summary Synthesizer
Generates:
1. Quick Consultation Snapshot (1-minute scan for OPD)
2. Detailed Clinical Case History (OPQRST & ROS)
3. Information Completeness Meter
4. Uncertainty & Contradiction Panel
5. Full Multilingual Consultation Transcripts
Strictly adheres to safety: AI produces draft clinical history, never final diagnoses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class ClinicalSummarySynthesizer:
    """Synthesizes comprehensive physician-facing reports from the clinical interview state."""

    @classmethod
    def calculate_completeness(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates completeness score (0-100%) and missing essential items."""
        hpi = state.get("hpi", {})
        core_params = ["duration", "severity", "location", "character", "onset", "triggers", "relievers"]

        completed = []
        missing = []

        for p in core_params:
            p_obj = hpi.get(p)
            val = p_obj.get("value") if isinstance(p_obj, dict) else p_obj
            if val is not None and str(val).strip():
                completed.append(p)
            else:
                missing.append(p)

        # Check chief complaint
        if state.get("chief_complaint"):
            completed.append("chief_complaint")
        else:
            missing.append("chief_complaint")

        # Check medications & allergies
        if state.get("medications_queried") or state.get("medications"):
            completed.append("medications")
        else:
            missing.append("medications")

        if state.get("allergies_queried") or state.get("allergies"):
            completed.append("allergies")
        else:
            missing.append("allergies")

        total = len(core_params) + 3
        score = int((len(completed) / total) * 100)

        return {
            "score_percent": score,
            "completed_count": len(completed),
            "total_count": total,
            "completed_parameters": completed,
            "missing_parameters": missing,
            "status": "COMPREHENSIVE" if score >= 80 else ("ADEQUATE" if score >= 50 else "INITIAL")
        }

    @classmethod
    def generate_quick_snapshot(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generates the high-yield 1-minute OPD consultation snapshot."""
        hpi = state.get("hpi", {})
        chief = state.get("chief_complaint") or "Unspecified complaint"
        dur_obj = hpi.get("duration")
        duration = (dur_obj.get("value") if isinstance(dur_obj, dict) else dur_obj) or "Unspecified duration"
        sev_obj = hpi.get("severity")
        severity = sev_obj.get("value") if isinstance(sev_obj, dict) else sev_obj
        severity_str = f"Pain/Discomfort: {severity}/10" if severity is not None else "Severity not rated"

        red_flags = state.get("red_flags_detected", [])
        urgency = state.get("triage_urgency", "ROUTINE")

        # Positive findings
        positives = []
        for k, v in hpi.items():
            val = v.get("value") if isinstance(v, dict) else v
            if val and k not in ["pertinent_negatives"]:
                if isinstance(val, list):
                    positives.append(f"{k.replace('_', ' ').title()}: {', '.join(str(x) for x in val)}")
                else:
                    positives.append(f"{k.replace('_', ' ').title()}: {val}")

        # Pertinent negatives
        negatives = state.get("pertinent_negatives", [])
        if not negatives and "associated_symptoms" in hpi:
            neg_val = hpi.get("pertinent_negatives", {}).get("value", [])
            if isinstance(neg_val, list):
                negatives = neg_val

        meds = state.get("medications", [])
        allergies = state.get("allergies", [])

        # Differential suggestions base
        diff_suggestions = cls._generate_differentials(chief, hpi, red_flags)

        return {
            "title": "Quick Consultation Snapshot (OPD Rapid Read)",
            "disclaimer": "DRAFT — For physician clinical evaluation only. AI is an assistive history tool, not a diagnostic authority.",
            "chief_complaint": f"{chief} ({duration})",
            "triage_urgency": urgency,
            "severity": severity_str,
            "red_flags": red_flags,
            "key_positives": positives[:6],
            "pertinent_negatives": negatives[:6] if negatives else ["None explicitly recorded"],
            "current_medications": meds if meds else ["None reported"],
            "known_allergies": allergies if allergies else ["None reported"],
            "provisional_differentials": diff_suggestions
        }

    @classmethod
    def generate_detailed_history(cls, state: Dict[str, Any], documents: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generates comprehensive structured clinical history."""
        hpi = state.get("hpi", {})
        chief = state.get("chief_complaint", "Not specified")

        def _get_val(key: str, default: str = "Not elicited") -> Any:
            item = hpi.get(key)
            if isinstance(item, dict):
                v = item.get("value")
                return v if v is not None and str(v).strip() != "" else default
            elif item is not None and str(item).strip() != "":
                return item
            return default

        # OPQRST breakdown
        opqrst = {
            "Onset": _get_val("onset", "Not elicited"),
            "Provocation / Triggers": _get_val("triggers", "Not elicited"),
            "Palliation / Relievers": _get_val("relievers", "Not elicited"),
            "Quality / Character": _get_val("character", "Not elicited"),
            "Region / Radiation": f"Site: {_get_val('location', 'N/A')}, Radiation: {_get_val('radiation', 'None')}",
            "Severity": f"{_get_val('severity', 'Not rated')} / 10" if _get_val('severity', 'Not rated') != "Not rated" else "Not rated",
            "Timing / Duration": _get_val("duration", "Not elicited")
        }

        # Review of Systems
        ros = state.get("review_of_systems", {})

        # Timeline
        from .provenance import ProvenanceTracker
        timeline = ProvenanceTracker.synthesize_timeline(state, documents)

        return {
            "title": "Comprehensive Clinical Case History",
            "chief_complaint": chief,
            "hpi_narrative": cls._build_hpi_narrative(chief, hpi),
            "opqrst_table": opqrst,
            "review_of_systems": ros if ros else {"General": "Elicited during primary complaint interview"},
            "past_medical_history": state.get("past_history", "None reported"),
            "family_history": state.get("family_history", "Non-contributory"),
            "medication_reconciliation": {
                "active_medications": state.get("medications", []),
                "adherence": state.get("medication_adherence", "Reported compliant"),
                "allergies": state.get("allergies", [])
            },
            "chronological_timeline": timeline
        }

    @classmethod
    def synthesize_full_review(
        cls,
        state: Dict[str, Any],
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Produces the complete suite of physician consultation outputs."""
        completeness = cls.calculate_completeness(state)
        snapshot = cls.generate_quick_snapshot(state)
        detailed = cls.generate_detailed_history(state, documents)
        transcripts = state.get("conversation_history", [])
        contradictions = state.get("contradictions", [])
        uncertainties = state.get("uncertainties", [])
        red_flags = state.get("red_flags_detected", [])
        provenance = state.get("source_provenance", [])

        return {
            "case_id": state.get("case_id"),
            "patient_id": state.get("patient_id"),
            "primary_language": state.get("primary_language", "en-IN"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "READY_FOR_PHYSICIAN_VERIFICATION",
            "disclaimer": "AI-generated draft — physician verification required.",
            "completeness": completeness,
            "quick_snapshot": snapshot,
            "detailed_case_history": detailed,
            "red_flags": red_flags,
            "uncertainties": uncertainties,
            "contradictions": contradictions,
            "documents": documents or [],
            "timeline": detailed.get("chronological_timeline", []),
            "source_provenance": provenance,
            "transcripts": transcripts,
            "ayush_notes": state.get("ayush_parameters", {})
        }

    @classmethod
    def _build_hpi_narrative(cls, chief: str, hpi: Dict[str, Any]) -> str:
        """Constructs an articulate medical narrative from HPI elements."""
        def _get_v(key: str) -> Any:
            item = hpi.get(key)
            if isinstance(item, dict):
                return item.get("value")
            return item

        dur = _get_v("duration")
        sev = _get_v("severity")
        loc = _get_v("location")
        char = _get_v("character")
        trig = _get_v("triggers")
        rel = _get_v("relievers")
        rad = _get_v("radiation")

        parts = [f"Patient presents with {chief}"]
        if dur:
            parts.append(f"persisting for {dur}.")
        else:
            parts.append("of unstated duration.")

        desc_parts = []
        if loc:
            desc_parts.append(f"located in the {loc}")
        if char:
            desc_parts.append(f"characterized as {char}")
        if sev is not None:
            desc_parts.append(f"rated at {sev}/10 in severity")
        if rad and rad.lower() != "none":
            desc_parts.append(f"radiating to {rad}")

        if desc_parts:
            parts.append("The discomfort is " + ", ".join(desc_parts) + ".")

        if trig:
            parts.append(f"Symptoms are reported to be aggravated by {trig}.")
        if rel:
            parts.append(f"Partial relief is noted with {rel}.")

        return " ".join(parts)

    @classmethod
    def _generate_differentials(cls, chief: str, hpi: Dict[str, Any], red_flags: List[Any]) -> List[Dict[str, Any]]:
        """Provides supportive differential considerations for physician reference."""
        c = chief.lower()
        diffs = []

        if any(x in c for x in ["chest pain", "angina"]):
            diffs.append({"condition": "Acute Coronary Syndrome / Angina", "rationale": "Chest discomfort, cardiac risk profile"})
            diffs.append({"condition": "Gastroesophageal Reflux Disease (GERD)", "rationale": "Burning retrosternal discomfort aggravated postprandially"})
            diffs.append({"condition": "Musculoskeletal Chest Wall Strain", "rationale": "Localized chest tenderness without hemodynamic compromise"})
        elif any(x in c for x in ["cough", "breath", "fever"]):
            diffs.append({"condition": "Acute Bronchitis / Viral Upper Respiratory Infection", "rationale": "Cough with low-to-moderate fever and constitutional symptoms"})
            diffs.append({"condition": "Community Acquired Pneumonia", "rationale": "Productive cough with systemic signs"})
            diffs.append({"condition": "Reactive Airway Disease / Asthma exacerbation", "rationale": "Wheezing or breathlessness triggered by environmental factors"})
        elif any(x in c for x in ["headache", "head pain", "migraine"]):
            diffs.append({"condition": "Tension-type Headache", "rationale": "Bilateral band-like pressure, aggravated by stress"})
            diffs.append({"condition": "Migraine without Aura", "rationale": "Unilateral throbbing headache with photophobia or nausea"})
            diffs.append({"condition": "Cervicogenic Headache", "rationale": "Occipital pain related to posture and neck stiffness"})
        elif any(x in c for x in ["stomach", "abdomen", "abdominal pain", "loose motions"]):
            diffs.append({"condition": "Acute Gastroenteritis", "rationale": "Abdominal cramping with nausea and loose stools"})
            diffs.append({"condition": "Acid Peptic Disease / Gastritis", "rationale": "Epigastric burning related to meals"})
            diffs.append({"condition": "Irritable Bowel Syndrome", "rationale": "Recurrent discomfort relieved by defecation"})
        else:
            diffs.append({"condition": "Primary Presentation: " + chief.title(), "rationale": "Clinical evaluation recommended for definitive diagnosis"})

        return diffs
