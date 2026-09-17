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
except ImportError:
    try:
        import database as db
        import case_taking_engine as engine
        import report_extractor
    except ImportError:
        from api import database as db
        from api import case_taking_engine as engine
        from api import report_extractor

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
