"""
MedLens Clinical Interview Engine — Contradiction Engine
Detects discrepancies between patient statements and uploaded documents (prescriptions/lab tests),
as well as internal self-contradictions during the interview.
"""

from typing import Dict, Any, List, Optional
import re


class ContradictionEngine:
    """Cross-references patient reported data with document extractions and prior statements."""

    @classmethod
    def check_document_vs_patient(
        cls,
        patient_state: Dict[str, Any],
        document_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Cross-checks current interview state against parsed documents.
        Returns a list of contradiction objects.
        """
        contradictions = []

        def _to_str(item):
            if isinstance(item, dict):
                return str(item.get("name") or item.get("value") or "").lower().strip()
            return str(item or "").lower().strip()

        patient_meds = [_to_str(m) for m in patient_state.get("medications", []) if _to_str(m)]
        patient_allergies = [_to_str(a) for a in patient_state.get("allergies", []) if _to_str(a)]
        doc_meds = [_to_str(m) for m in document_data.get("medications", []) if _to_str(m)]
        doc_allergies = [_to_str(a) for a in document_data.get("allergies", []) if _to_str(a)]
        doc_diagnoses = [_to_str(d) for d in document_data.get("diagnoses", []) if _to_str(d)]
        raw_doc_text = str(document_data.get("raw_text", "")).lower()

        # 1. Medication discrepancy: Patient claims no meds, but document lists meds
        has_negative_med_statement = any(
            re.search(r"\b(no\s+.*med\w*|no\s+med\w*|none|nothing|not\s+taking\s+any|do\s+not\s+take|koyi\s+dawai\s+nahi|mandulu\s+levu)\b", str(m), re.IGNORECASE)
            for m in patient_meds
        ) or (len(patient_meds) == 0 and patient_state.get("medications_queried", False))

        if has_negative_med_statement and doc_meds:
            contradictions.append({
                "id": "CONTRADICTION_MED_DENIAL",
                "status": "UNRESOLVED",
                "category": "medications",
                "severity": "HIGH",
                "patient_claim": "Patient reported not taking any regular medications.",
                "document_claim": f"Active prescriptions: {', '.join(doc_meds)}",
                "document_evidence": f"Uploaded records indicate active prescriptions: {', '.join(doc_meds)}.",
                "discrepancy_description": f"Patient reported no medications, but document indicates active prescriptions: {', '.join(doc_meds)}.",
                "doctor_probe_question": f"Patient stated no current medications, but records show prior prescription for {', '.join(doc_meds)}. Confirm compliance or discontinuation.",
                "resolution_notes": "",
                "resolved_by": None,
                "resolved_at": None,
                "provenance": "document_crosscheck"
            })

        # Check specific medication omission
        for dm in doc_meds:
            if dm and not any(dm in pm for pm in patient_meds) and not has_negative_med_statement and patient_meds:
                contradictions.append({
                    "id": f"CONTRADICTION_MED_OMISSION_{dm[:10].upper()}",
                    "status": "UNRESOLVED",
                    "category": "medications",
                    "severity": "MEDIUM",
                    "patient_claim": f"Reported medications: {', '.join(patient_meds)}.",
                    "document_claim": f"Document lists {dm}",
                    "document_evidence": f"Document lists {dm} which was not mentioned by patient.",
                    "discrepancy_description": f"Document lists {dm} which was not reported in verbal medication history.",
                    "doctor_probe_question": f"Uploaded record lists '{dm}'. Ask patient if they are currently taking this.",
                    "resolution_notes": "",
                    "resolved_by": None,
                    "resolved_at": None,
                    "provenance": "document_crosscheck"
                })

        # 2. Allergy discrepancy: Patient claims no allergies, but record shows drug allergy
        has_negative_allergy = any(
            re.search(r"\b(no allerg\w*|none|nothing|koyi allergy nahi|allergy ledu)\b", str(a).lower())
            for a in patient_allergies
        )
        if has_negative_allergy and doc_allergies:
            contradictions.append({
                "id": "CONTRADICTION_ALLERGY_DENIAL",
                "status": "UNRESOLVED",
                "category": "allergies",
                "severity": "CRITICAL",
                "patient_claim": "Patient denied having any known drug allergies.",
                "document_claim": f"Documented allergy: {', '.join(doc_allergies)}",
                "document_evidence": f"Medical records flag known allergy: {', '.join(doc_allergies)}.",
                "discrepancy_description": f"High Alert: Patient denied allergies, but medical records flag allergy to {', '.join(doc_allergies)}.",
                "doctor_probe_question": f"High Alert: Record notes allergy to {', '.join(doc_allergies)}. Re-verify before prescribing.",
                "resolution_notes": "",
                "resolved_by": None,
                "resolved_at": None,
                "provenance": "document_crosscheck"
            })

        # 3. Chronic disease denial vs Lab findings / Diagnoses
        hpi = patient_state.get("hpi", {})
        chief_complaint = str(patient_state.get("chief_complaint", "")).lower()

        if "diabet" in raw_doc_text or any("diabet" in d for d in doc_diagnoses):
            past_history = str(patient_state.get("past_history", "")).lower()
            if "no diabetes" in past_history or "no illness" in past_history or "never had sugar" in past_history:
                contradictions.append({
                    "id": "CONTRADICTION_DIABETES_DENIAL",
                    "status": "UNRESOLVED",
                    "category": "diagnoses",
                    "severity": "HIGH",
                    "patient_claim": "Patient stated no history of diabetes/blood sugar.",
                    "document_claim": "Clinical document indicates Diabetes history / markers",
                    "document_evidence": "Uploaded clinical document indicates Diabetes Mellitus history / elevated glycemic markers.",
                    "discrepancy_description": "Patient stated no history of diabetes, but uploaded record indicates prior diabetes diagnosis or testing.",
                    "doctor_probe_question": "Clarify diabetes history and recent fasting glucose / HbA1c status.",
                    "resolution_notes": "",
                    "resolved_by": None,
                    "resolved_at": None,
                    "provenance": "document_crosscheck"
                })

        # 4. Lab value contradictions (e.g. HbA1c > 8% but patient thinks condition is controlled)
        hba1c_match = re.search(r"hba1c\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)", raw_doc_text)
        if hba1c_match:
            try:
                val = float(hba1c_match.group(1))
                if val >= 8.0:
                    contradictions.append({
                        "id": "CONTRADICTION_HBA1C_ELEVATED",
                        "status": "UNRESOLVED",
                        "category": "labs",
                        "severity": "MEDIUM",
                        "patient_claim": "Patient reported general mild symptoms / stable health.",
                        "document_claim": f"HbA1c test result: {val}%",
                        "document_evidence": f"Document shows markedly elevated HbA1c of {val}%.",
                        "discrepancy_description": f"Uploaded lab report shows uncontrolled HbA1c ({val}%).",
                        "doctor_probe_question": f"Uncontrolled HbA1c ({val}%). Review glycemic management and medication adherence.",
                        "resolution_notes": "",
                        "resolved_by": None,
                        "resolved_at": None,
                        "provenance": "document_crosscheck"
                    })
            except ValueError:
                pass

        return contradictions

    @classmethod
    def check_internal_contradiction(
        cls,
        patient_state: Dict[str, Any],
        new_parameter: str,
        new_value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if a new statement directly opposes an established statement in the same session.
        """
        hpi = patient_state.get("hpi", {})

        if new_parameter == "duration":
            existing_dur = hpi.get("duration", {}).get("value")
            if existing_dur and str(existing_dur).lower() != str(new_value).lower():
                if ("today" in str(existing_dur).lower() and ("month" in str(new_value).lower() or "year" in str(new_value).lower())) or \
                   ("today" in str(new_value).lower() and ("month" in str(existing_dur).lower() or "year" in str(existing_dur).lower())):
                    return {
                        "id": "INTERNAL_CONFLICT_DURATION",
                        "status": "UNRESOLVED",
                        "category": "timeline",
                        "severity": "MEDIUM",
                        "patient_claim": f"Later reported '{new_value}'.",
                        "document_claim": f"Earlier reported '{existing_dur}'.",
                        "document_evidence": "Self-reported conflict during same interview session.",
                        "discrepancy_description": f"Patient reported duration as '{existing_dur}' earlier, but later stated '{new_value}'.",
                        "doctor_probe_question": f"Patient mentioned symptoms began '{existing_dur}' earlier, then reported '{new_value}'. Clarify if acute flare on chronic issue.",
                        "resolution_notes": "",
                        "resolved_by": None,
                        "resolved_at": None,
                        "provenance": "interview_transcript"
                    }

        if new_parameter == "severity":
            existing_sev = hpi.get("severity", {}).get("value")
            if existing_sev is not None and new_value is not None:
                try:
                    e_num = int(existing_sev)
                    n_num = int(new_value)
                    if abs(e_num - n_num) >= 5:
                        return {
                            "id": "INTERNAL_CONFLICT_SEVERITY",
                            "status": "UNRESOLVED",
                            "category": "severity",
                            "severity": "LOW",
                            "patient_claim": f"Severity rated as {n_num}/10.",
                            "document_claim": f"Previously rated as {e_num}/10.",
                            "document_evidence": "Discrepancy in pain scale ratings during session.",
                            "discrepancy_description": f"Pain scale rating fluctuated significantly from {e_num}/10 to {n_num}/10.",
                            "doctor_probe_question": "Clarify whether pain fluctuates between mild and severe.",
                            "resolution_notes": "",
                            "resolved_by": None,
                            "resolved_at": None,
                            "provenance": "interview_transcript"
                        }
                except (ValueError, TypeError):
                    pass

        return None

    @classmethod
    def check_document_vs_document(
        cls,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Cross-checks multiple uploaded documents for conflicting parameters
        (e.g., conflicting dosages or divergent test results).
        """
        conflicts = []
        if not documents or len(documents) < 2:
            return conflicts

        extracted_list = [d.get("extracted_data", {}) for d in documents if isinstance(d, dict)]

        # Check for medication dose differences across documents
        med_map = {}
        for idx, ext in enumerate(extracted_list):
            doc_name = documents[idx].get("filename", f"Doc {idx+1}")
            for med in ext.get("medications", []):
                m_str = str(med).strip().lower()
                m_base = re.sub(r"\b\d+\s*(?:mg|mcg|g|ml)\b", "", m_str).strip()
                if m_base:
                    if m_base not in med_map:
                        med_map[m_base] = []
                    med_map[m_base].append((doc_name, m_str))

        for base_med, occurrences in med_map.items():
            if len(occurrences) >= 2:
                distinct_versions = set(o[1] for o in occurrences)
                if len(distinct_versions) >= 2:
                    conflicts.append({
                        "id": f"DOC_CONFLICT_MED_{base_med[:10].upper()}",
                        "status": "UNRESOLVED",
                        "category": "medications",
                        "severity": "MEDIUM",
                        "patient_claim": "Document discrepancy detected between uploaded records.",
                        "document_claim": "; ".join(f"{doc}: {val}" for doc, val in occurrences),
                        "document_evidence": "Multiple uploaded records show divergent formulations or dosages.",
                        "discrepancy_description": f"Divergent prescriptions found for '{base_med}': {'; '.join(f'{doc}: {val}' for doc, val in occurrences)}",
                        "doctor_probe_question": f"Review active dosage for '{base_med}' as multiple records show different instructions.",
                        "resolution_notes": "",
                        "resolved_by": None,
                        "resolved_at": None,
                        "provenance": "document_crosscheck"
                    })

        return conflicts

