"""
MedLens Clinical Interview Engine — Provenance & Medical Timeline
Tracks exact source attribution for every captured clinical fact and synthesizes
a chronological medical timeline for the physician console.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re


class ProvenanceTracker:
    """Manages fact-level provenance and builds the chronological medical timeline."""

    VALID_SOURCES = {
        "patient_voice",
        "patient_text",
        "document_ocr",
        "past_ehr",
        "clinician_edit",
        "inferred"
    }

    @classmethod
    def create_provenance_entry(
        cls,
        field: str,
        value: Any,
        source: str = "patient_voice",
        confidence: float = 0.9,
        raw_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates an audit-ready provenance record."""
        source_sanitized = source if source in cls.VALID_SOURCES else "patient_voice"
        return {
            "field": field,
            "value": value,
            "source": source_sanitized,
            "confidence": round(confidence, 2),
            "raw_text": raw_text or "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def synthesize_timeline(
        cls,
        patient_state: Dict[str, Any],
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes a chronological event timeline from HPI, past history, and documents.
        Returns a sorted list of timeline event items.
        """
        timeline: List[Dict[str, Any]] = []

        # 1. Historical / chronic events from state
        past_hx = patient_state.get("past_history", [])
        if isinstance(past_hx, str) and past_hx:
            timeline.append({
                "period": "Past Medical History",
                "relative_order": -100,
                "event": past_hx,
                "source": "patient_reported",
                "category": "history"
            })
        elif isinstance(past_hx, list):
            for item in past_hx:
                timeline.append({
                    "period": "Past Medical History",
                    "relative_order": -100,
                    "event": str(item),
                    "source": "patient_reported",
                    "category": "history"
                })

        # 2. Document records (prior prescriptions / lab reports)
        if documents:
            for doc in documents:
                doc_title = doc.get("filename") or doc.get("title") or "Uploaded Medical Document"
                doc_date = doc.get("date") or doc.get("timestamp") or "Prior Record"
                doc_summary = doc.get("summary") or doc.get("findings") or doc.get("raw_text", "")[:120]
                timeline.append({
                    "period": str(doc_date),
                    "relative_order": -50,
                    "event": f"Document: {doc_title} — {doc_summary}",
                    "source": "document_ocr",
                    "category": "document"
                })

        # 3. Current illness episode
        hpi = patient_state.get("hpi", {})
        chief_complaint = patient_state.get("chief_complaint") or "Reported symptoms"
        duration_obj = hpi.get("duration", {})
        duration_val = duration_obj.get("value") if isinstance(duration_obj, dict) else duration_obj
        onset_obj = hpi.get("onset", {})
        onset_val = onset_obj.get("value") if isinstance(onset_obj, dict) else onset_obj

        # Parse relative timeline from duration
        order_num = -10
        period_str = "Onset of Current Episode"
        if duration_val:
            d_str = str(duration_val).lower()
            if "month" in d_str:
                order_num = -30
                period_str = f"{duration_val} ago"
            elif "week" in d_str:
                order_num = -20
                period_str = f"{duration_val} ago"
            elif "day" in d_str:
                order_num = -10
                period_str = f"{duration_val} ago"
            elif "today" in d_str or "hour" in d_str:
                order_num = -2
                period_str = "Today / Recent hours"

        onset_detail = f" (Onset: {onset_val})" if onset_val else ""
        timeline.append({
            "period": period_str,
            "relative_order": order_num,
            "event": f"Chief complaint onset: {chief_complaint}{onset_detail}",
            "source": "patient_voice",
            "category": "chief_complaint"
        })

        # Progression / Associated symptoms
        assoc = hpi.get("associated_symptoms", {})
        assoc_val = assoc.get("value") if isinstance(assoc, dict) else assoc
        if assoc_val:
            assoc_list = assoc_val if isinstance(assoc_val, list) else [str(assoc_val)]
            timeline.append({
                "period": "Progression",
                "relative_order": -5,
                "event": f"Associated symptoms developed: {', '.join(assoc_list)}",
                "source": "patient_voice",
                "category": "progression"
            })

        # Today's consultation
        sev_obj = hpi.get("severity", {})
        sev_val = sev_obj.get("value") if isinstance(sev_obj, dict) else sev_obj
        sev_str = f" Severity rated: {sev_val}/10." if sev_val is not None else ""
        timeline.append({
            "period": "Today (Consultation)",
            "relative_order": 0,
            "event": f"Presenting for clinical evaluation.{sev_str}",
            "source": "consultation_intake",
            "category": "consultation"
        })

        # Sort timeline by relative order
        timeline.sort(key=lambda x: x.get("relative_order", 0))
        return timeline
