"""
MEDLENS AI x Medicover — Clinical Case-Taking API Router
Implements the SIH 'Patient Case-Taking Software' REST endpoints:
- Case Initialization & Consent Validation
- Adaptive Question Generation
- Structured History Section Persistence
- Medical Document Linking (Reusing MEDLENS Report Extractor)
- Physician-Ready Summary Generation & Red Flag Triage
- Doctor Console Review, Edit, & Sign-off Workflow
"""

import os
import json
import secrets
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form, status
from pydantic import BaseModel, Field

try:
    from disease_prediction.api import database as db
    from disease_prediction.api import case_taking_engine as engine
    from disease_prediction.api import report_extractor
    from disease_prediction.api import clinical_interview as ci
except ImportError:
    try:
        import database as db
        import case_taking_engine as engine
        import report_extractor
        import clinical_interview as ci
    except ImportError:
        from api import database as db
        from api import case_taking_engine as engine
        from api import report_extractor
        from api import clinical_interview as ci

router = APIRouter(prefix="/api/cases", tags=["SIH Clinical Case-Taking"])


# ==============================================================================
# PYDANTIC SCHEMAS
# ==============================================================================
class CaseStartRequest(BaseModel):
    patient_id: str
    chief_complaint: str = ""
    abha_id: Optional[str] = None
    consent_given: bool = True
    consent_text: str = "Standard SIH Patient Consent for Digital Clinical Case-Taking & Medical Records Processing"

class SaveSectionRequest(BaseModel):
    section_id: str
    section_title: str
    raw_input: str
    structured_data: Optional[Dict[str, Any]] = None
    input_mode: str = "text"  # 'voice', 'text', 'guided_options'

class AdaptiveQuestionsRequest(BaseModel):
    chief_complaint: str = ""
    answers: Dict[str, Any] = {}

class GenerateSummaryRequest(BaseModel):
    chief_complaint: Optional[str] = None
    ayush_data: Optional[Dict[str, Any]] = None

class DoctorReviewRequest(BaseModel):
    doctor_id: str = "Dr. Medicover Clinical Desk"
    doctor_notes: str = ""
    updated_summary: Optional[Dict[str, Any]] = None
    status: str = "confirmed"

class AttachDocumentRequest(BaseModel):
    report_id: Optional[str] = None
    document_type: str = "lab_report"
    filename: str
    extracted_data: Optional[Dict[str, Any]] = None

class InterviewStartRequest(BaseModel):
    patient_id: str
    case_id: Optional[str] = None
    language_code: str = "en-IN"
    chief_complaint: Optional[str] = None
    is_kiosk: bool = False

class InterviewRespondRequest(BaseModel):
    case_id: str
    answer_text: str
    current_question_id: Optional[str] = None
    language_code: str = "en-IN"
    input_mode: str = "voice"
    confidence: Optional[float] = 0.9

class InterviewCorrectFactRequest(BaseModel):
    case_id: str
    parameter_name: str
    corrected_value: Any
    correction_reason: Optional[str] = "Patient correction"

class InterviewVerifyDocRequest(BaseModel):
    case_id: str
    document_data: Dict[str, Any]


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/sections")
def get_clinical_sections():
    """Returns the 10 standard clinical case-taking history sections."""
    return {"sections": engine.CLINICAL_SECTIONS}

@router.get("/ayush-fields")
def get_ayush_fields():
    """Returns optional AYUSH clinical assessment fields."""
    return {"fields": engine.AYUSH_FIELDS}

@router.post("/start")
def start_case_session(payload: CaseStartRequest):
    """Initializes a new case-taking session with explicit consent."""
    if not payload.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient consent is mandatory before starting clinical case taking."
        )

    patient = db.get_patient_by_id(payload.patient_id)
    if not patient:
        try:
            db.create_patient(
                patient_id=payload.patient_id,
                name="Clinical Case Patient",
                age=32,
                gender="Male",
                contact="+91-9876543210",
                email="patient@medlens.org",
                access_pin="PIN-1000"
            )
            patient = db.get_patient_by_id(payload.patient_id)
        except Exception:
            all_p = db.get_all_patients()
            patient = all_p[0] if all_p else None

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient ID '{payload.patient_id}' could not be registered or found."
        )

    target_patient_id = patient["patient_id"]
    case_row = db.create_clinical_case(
        patient_id=target_patient_id,
        chief_complaint=payload.chief_complaint,
        abha_id=payload.abha_id,
        consent_text=payload.consent_text
    )

    return {
        "status": "initialized",
        "case_id": case_row["case_id"],
        "patient_id": target_patient_id,
        "patient_name": patient.get("name", "Outpatient"),
        "created_at": case_row["created_at"],
        "message": "Clinical case taking initialized with consent."
    }

@router.get("/{case_id}")
def get_case_details(case_id: str):
    """Retrieves full case details, history sections, attached documents, and summary."""
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
    return case

@router.get("/patient/{patient_id}")
def get_patient_cases(patient_id: str):
    """Retrieves all clinical cases for a specific patient."""
    cases = db.list_patient_clinical_cases(patient_id)
    return {"patient_id": patient_id, "cases": cases}

@router.get("/all/list")
def list_all_cases(limit: int = 50):
    """Lists recent clinical cases for the Doctor Console triage board."""
    cases = db.list_all_clinical_cases(limit=limit)
    return {"cases": cases, "total": len(cases)}

@router.post("/{case_id}/adaptive-questions")
def get_adaptive_questions_endpoint(case_id: str, payload: AdaptiveQuestionsRequest):
    """Generates adaptive, contextual follow-up questions based on patient's answers."""
    questions = engine.get_adaptive_questions(
        chief_complaint=payload.chief_complaint,
        answers=payload.answers
    )
    return {"case_id": case_id, "questions": questions}

@router.post("/{case_id}/save-section")
def save_section_endpoint(case_id: str, payload: SaveSectionRequest):
    """Saves or updates a structured history section (Text or Voice recognized)."""
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    res = db.save_case_section(
        case_id=case_id,
        section_id=payload.section_id,
        section_title=payload.section_title,
        raw_input=payload.raw_input,
        structured_data=payload.structured_data or {},
        input_mode=payload.input_mode
    )
    return res

@router.post("/{case_id}/attach-document")
def attach_document_endpoint(case_id: str, payload: AttachDocumentRequest):
    """Associates an existing laboratory report or external medical document with the case."""
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    extracted_data = payload.extracted_data or {}
    
    # If report_id is provided and extracted_data is empty, fetch official report data
    if payload.report_id and not extracted_data:
        rep = db.get_report_by_id(payload.report_id)
        if rep:
            extracted_data = rep.get("report_data", {})

    res = db.save_case_document(
        case_id=case_id,
        report_id=payload.report_id,
        document_type=payload.document_type,
        filename=payload.filename,
        extracted_data=extracted_data
    )
    return res

@router.post("/{case_id}/upload-and-attach-file")
async def upload_and_attach_file(
    case_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("lab_report")
):
    """
    Uploads a new PDF/image file, parses parameters via MEDLENS Report Extractor,
    and attaches it to the active clinical case sheet.
    """
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    extracted_data = {}
    try:
        if file.filename.lower().endswith(".pdf"):
            ext_res = report_extractor.extract_from_pdf_bytes(file_bytes, file.filename)
            extracted_data = ext_res.get("extracted_parameters", {})
        elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            ext_res = report_extractor.extract_from_image_bytes(file_bytes, file.filename)
            extracted_data = ext_res.get("extracted_parameters", {})
        elif file.filename.lower().endswith(".txt"):
            ext_res = report_extractor.extract_from_text_str(file_bytes.decode("utf-8", errors="ignore"), file.filename)
            extracted_data = ext_res.get("extracted_parameters", {})
    except Exception as ex:
        extracted_data = {"raw_note": f"Document uploaded ({file.filename}) - Manual review required: {str(ex)}"}

    res = db.save_case_document(
        case_id=case_id,
        report_id=None,
        document_type=document_type,
        filename=file.filename,
        extracted_data=extracted_data
    )
    res["extracted_data"] = extracted_data
    return res

@router.post("/{case_id}/generate-summary")
def generate_physician_summary_endpoint(case_id: str, payload: GenerateSummaryRequest):
    """
    Compiles all patient recorded sections, linked documents, and red flags
    into a physician-ready structured summary sheet and marks the case as 'submitted'.
    """
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    patient = db.get_patient_by_id(case["patient_id"]) or {
        "patient_id": case["patient_id"],
        "name": case.get("patient_name", "Outpatient"),
        "age": case.get("patient_age", 30),
        "gender": case.get("patient_gender", "Other"),
        "contact": case.get("patient_contact", "—")
    }

    chief_complaint = payload.chief_complaint or case.get("chief_complaint")
    summary = engine.synthesize_physician_summary(
        patient_info=patient,
        case_info=case,
        sections=case.get("sections", []),
        documents=case.get("documents", []),
        ayush_data=payload.ayush_data
    )

    triage_urgency = summary.get("triage_level", "routine")
    red_flags = [f.get("message") for f in summary.get("red_flags", [])]

    db.update_case_summary_and_triage(
        case_id=case_id,
        summary_data=summary,
        triage_urgency=triage_urgency,
        red_flags=red_flags,
        ayush_data=payload.ayush_data,
        chief_complaint=chief_complaint
    )

    return {
        "status": "submitted",
        "case_id": case_id,
        "triage_urgency": triage_urgency,
        "has_red_flags": len(red_flags) > 0,
        "summary": summary
    }

@router.post("/{case_id}/doctor-review")
def doctor_review_endpoint(case_id: str, payload: DoctorReviewRequest):
    """Allows attending doctor to edit, verify, sign-off, and add notes to the case sheet."""
    case = db.get_clinical_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    res = db.doctor_review_case(
        case_id=case_id,
        doctor_id=payload.doctor_id,
        doctor_notes=payload.doctor_notes,
        updated_summary=payload.updated_summary,
        status=payload.status
    )
    return res


# ==============================================================================
# UNIFIED CLINICAL INTERVIEW ENGINE ENDPOINTS (SIH PS 26047)
# ==============================================================================

@router.post("/interview/start")
def start_interview_endpoint(payload: InterviewStartRequest):
    """
    Initializes a structured conversational clinical interview session.
    Always starts with the required open-ended prompt:
    'Please tell me in your own words what is bothering you today.'
    """
    case_id = payload.case_id
    if not case_id:
        case_data = db.create_clinical_case(
            patient_id=payload.patient_id,
            chief_complaint=payload.chief_complaint or "",
            abha_id=None,
            consent_text="Digital Clinical Interview Consent"
        )
        case_id = case_data["case_id"]

    state = db.get_case_interview_state(case_id)
    if not state:
        state = ci.create_initial_patient_state(
            case_id=case_id,
            patient_id=payload.patient_id,
            primary_language=payload.language_code,
            is_kiosk=payload.is_kiosk
        )
        if payload.chief_complaint:
            state = ci.PatientStateManager.set_chief_complaint(state, payload.chief_complaint, source="pre_registration")

    first_q = ci.ClinicalQuestionEngine.generate_open_ended_first_question(payload.language_code)
    db.save_case_interview_state(case_id, state)

    return {
        "status": "active",
        "case_id": case_id,
        "patient_id": payload.patient_id,
        "language_code": payload.language_code,
        "current_question": first_q,
        "completeness": ci.ClinicalSummarySynthesizer.calculate_completeness(state),
        "state": ci.PatientStateManager.sanitize_for_export(state, is_physician_view=False)
    }

@router.post("/interview/respond")
def respond_interview_endpoint(payload: InterviewRespondRequest):
    """
    Core conversational interview step:
    1. Red flag scan (immediate pause and patient instructions if positive).
    2. Answer entity extraction & confidence check.
    3. State update & provenance tracking.
    4. Contradiction & ambiguity check.
    5. Priority-driven next question selection with gap analysis.
    """
    state = db.get_case_interview_state(payload.case_id)
    if not state:
        case = db.get_clinical_case(payload.case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' not found.")
        state = ci.create_initial_patient_state(
            case_id=payload.case_id,
            patient_id=case["patient_id"],
            primary_language=payload.language_code
        )

    # 1. Evaluate Red Flags
    rf_match = ci.RedFlagEngine.evaluate(payload.answer_text, payload.language_code)
    if rf_match:
        state = ci.PatientStateManager.add_red_flag(state, rf_match)
        state = ci.PatientStateManager.append_conversation_turn(
            state,
            speaker="patient",
            text=payload.answer_text,
            language=payload.language_code,
            audio_confidence=payload.confidence or 0.9,
            extracted_entities={"red_flag": rf_match}
        )
        db.save_case_interview_state(payload.case_id, state)
        return ci.RedFlagEngine.format_interruption_response(rf_match, payload.language_code)

    # 2. Extract clinical entities
    extracted = ci.ClinicalAnswerExtractor.extract_from_text(
        text=payload.answer_text,
        target_parameter=payload.current_question_id,
        language=payload.language_code
    )

    # Set chief complaint if this is the opening answer
    if not state.get("chief_complaint") or state.get("chief_complaint") == "Unspecified complaint":
        symptoms = extracted.get("associated_symptoms", {}).get("value", [])
        if symptoms and isinstance(symptoms, list):
            state = ci.PatientStateManager.set_chief_complaint(state, ", ".join(symptoms[:2]), source=payload.input_mode)
        elif payload.answer_text:
            state = ci.PatientStateManager.set_chief_complaint(state, payload.answer_text[:80], source=payload.input_mode)

    # 3. Update state with extracted parameters
    source_name = "patient_voice" if payload.input_mode == "voice" else "patient_text"
    for param_name, param_obj in extracted.items():
        if param_obj.get("value") is not None:
            state = ci.PatientStateManager.update_hpi_parameter(
                state=state,
                parameter_name=param_name,
                value=param_obj["value"],
                source=source_name,
                confidence=param_obj.get("confidence", 0.85),
                raw_text=param_obj.get("raw_text", payload.answer_text)
            )

    # 4. Check for internal self-contradictions
    for p_name, p_obj in extracted.items():
        if p_obj.get("value") is not None:
            internal_contra = ci.ContradictionEngine.check_internal_contradiction(
                state, p_name, p_obj["value"]
            )
            if internal_contra:
                ci.PatientStateManager.add_contradiction(state, internal_contra)

    # Append turn to transcript
    state = ci.PatientStateManager.append_conversation_turn(
        state,
        speaker="patient",
        text=payload.answer_text,
        language=payload.language_code,
        audio_confidence=payload.confidence or 0.9,
        extracted_entities=extracted
    )

    # 5. Evaluate confidence & clarifications
    needs_clarification = False
    clarification_question = None
    for p_name, p_obj in extracted.items():
        conf_eval = ci.ConfidenceManager.evaluate_extraction(
            p_name, p_obj, payload.answer_text, payload.language_code
        )
        if conf_eval.get("needs_clarification"):
            needs_clarification = True
            clarification_question = {
                "id": f"CLARIFY_{p_name.upper()}",
                "parameter": p_name,
                "priority": "P1",
                "question": {payload.language_code: conf_eval["clarification_prompt"]},
                "quick_picks": {payload.language_code: ["Not sure", "Mild", "Severe"]}
            }
            ci.PatientStateManager.add_uncertainty(state, {
                "parameter": p_name,
                "raw_text": payload.answer_text,
                "reason": "Low confidence extraction",
                "confidence": conf_eval["confidence"]
            })
            break

    # 6. Select next question
    if needs_clarification and clarification_question:
        next_q = clarification_question
    else:
        next_q = ci.ClinicalQuestionEngine.select_next_question(
            patient_state=state,
            current_language=payload.language_code,
            last_answer_entities=extracted
        )

    if next_q:
        q_text = next_q.get("question", {}).get(payload.language_code) or next_q.get("question", {}).get("en-IN") or ""
        state = ci.PatientStateManager.append_conversation_turn(
            state,
            speaker="assistant",
            text=q_text,
            language=payload.language_code,
            audio_confidence=1.0,
            extracted_entities={"question_id": next_q.get("id")}
        )

    db.save_case_interview_state(payload.case_id, state)
    completeness = ci.ClinicalSummarySynthesizer.calculate_completeness(state)
    is_complete = next_q is None or completeness["score_percent"] >= 90

    return {
        "status": "completed" if is_complete else "active",
        "case_id": payload.case_id,
        "next_question": next_q,
        "is_complete": is_complete,
        "completeness": completeness,
        "extracted_entities": extracted,
        "state": ci.PatientStateManager.sanitize_for_export(state, is_physician_view=False)
    }

@router.post("/interview/correct-fact")
def correct_fact_endpoint(payload: InterviewCorrectFactRequest):
    """Allows patient or clinician to explicitly rectify a previously noted fact."""
    state = db.get_case_interview_state(payload.case_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' state not found.")

    state = ci.PatientStateManager.correct_fact(
        state=state,
        parameter_name=payload.parameter_name,
        new_value=payload.corrected_value,
        corrected_by="patient_correction",
        reason=payload.correction_reason or "Direct correction"
    )
    db.save_case_interview_state(payload.case_id, state)

    return {
        "status": "corrected",
        "case_id": payload.case_id,
        "parameter_name": payload.parameter_name,
        "new_value": payload.corrected_value,
        "completeness": ci.ClinicalSummarySynthesizer.calculate_completeness(state)
    }

@router.post("/interview/verify-document")
def verify_document_endpoint(payload: InterviewVerifyDocRequest):
    """Cross-references uploaded documents with interview statements."""
    state = db.get_case_interview_state(payload.case_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' state not found.")

    contradictions = ci.ContradictionEngine.check_document_vs_patient(state, payload.document_data)
    for c in contradictions:
        ci.PatientStateManager.add_contradiction(state, c)

    db.save_case_interview_state(payload.case_id, state)
    return {
        "case_id": payload.case_id,
        "contradictions_detected": contradictions,
        "count": len(contradictions)
    }

@router.get("/interview/{case_id}/state")
def get_interview_state_endpoint(case_id: str, view: str = "patient"):
    """Returns the patient state, sanitized according to view mode (patient vs physician)."""
    state = db.get_case_interview_state(case_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No interview state found for case '{case_id}'.")
    is_physician = (view.lower() in ["physician", "doctor"])
    return ci.PatientStateManager.sanitize_for_export(state, is_physician_view=is_physician)

@router.get("/interview/{case_id}/review")
def get_interview_review_endpoint(case_id: str):
    """Generates the full physician review package: Quick Snapshot, Detailed Case History, Contradictions, Transcripts."""
    state = db.get_case_interview_state(case_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No interview state found for case '{case_id}'.")

    case = db.get_clinical_case(case_id)
    docs = case.get("documents", []) if case else []
    review_package = ci.ClinicalSummarySynthesizer.synthesize_full_review(state, docs)
    return review_package

@router.post("/interview/{case_id}/finalize")
def finalize_interview_endpoint(case_id: str):
    """Finalizes the interview, updates clinical_cases summary and triage, marks ready for doctor sign-off."""
    state = db.get_case_interview_state(case_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No interview state found for case '{case_id}'.")

    case = db.get_clinical_case(case_id)
    docs = case.get("documents", []) if case else []
    review_pkg = ci.ClinicalSummarySynthesizer.synthesize_full_review(state, docs)

    triage_urgency = state.get("triage_urgency", "ROUTINE").lower()
    red_flags = [rf.get("flag_id", str(rf)) for rf in state.get("red_flags_detected", [])]

    db.update_case_summary_and_triage(
        case_id=case_id,
        summary_data=review_pkg,
        triage_urgency=triage_urgency,
        red_flags=red_flags,
        ayush_data=state.get("ayush_parameters"),
        chief_complaint=state.get("chief_complaint", "")
    )

    return {
        "status": "finalized",
        "case_id": case_id,
        "triage_urgency": triage_urgency,
        "review_package": review_pkg
    }

