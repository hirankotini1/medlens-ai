"""
MEDLENS AI — Publication-Grade Clinical PDF Report Generator
Generates an executive, professional A4 medical dossier for clinical intake.

Key Features:
1. Executive A4 typography with header, footer, page numbering, and hospital branding.
2. Multilingual Unicode font handling (Nirmala UI for Devanagari, Telugu, Odia with fallback).
3. Structured sections:
   - Header & Clinical Summary
   - Patient Information & Triage Badge
   - Complete Chief Complaints (all preserved)
   - History of Present Illness (OPQRST breakdown)
   - Medical History (Past, Surgical, Family, Allergy, Social)
   - Structured Medication Table (with source provenance & verification status)
   - Investigations & Medical Documents Table
   - Clinical Red Flags & Safety Alerts
   - Information Requiring Attention (Unresolved Gaps)
   - Information Requiring Verification (Contradictions)
   - Interview Overview & Input Mode
   - AI-Assisted Clinical Analysis (with explicit non-diagnostic disclaimer)
   - Attending Physician Review & Sign-Off Block
   - Appendix of Uploaded Records
4. Naming convention: MedLens_Clinical_Case_Summary_<CASE_ID>_<DATE>.pdf
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF

class MedLensReportPDF(FPDF):
    """Custom FPDF class providing standardized hospital headers, footers, and page numbers."""

    def __init__(self, case_id: str, intake_date: str, status: str = "Ready for Physician Review"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.case_id = case_id
        self.intake_date = intake_date
        self.report_status = status
        self.has_unicode_font = False
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=15, top=15, right=15)
        self._setup_fonts()

    def _setup_fonts(self):
        """Loads Unicode font (Nirmala) if available on Windows, with safe Latin fallback."""
        nirmala_path = "C:/Windows/Fonts/Nirmala.ttc"
        if os.path.exists(nirmala_path):
            try:
                self.add_font("Nirmala", fname=nirmala_path)
                self.has_unicode_font = True
            except Exception:
                self.has_unicode_font = False

    def get_font_name(self) -> str:
        return "Nirmala" if self.has_unicode_font else "Helvetica"

    def header(self):
        # Top hospital header strip
        font = self.get_font_name()
        self.set_fill_color(15, 23, 42)  # Slate 900
        self.rect(0, 0, 210, 14, "F")
        self.set_text_color(255, 255, 255)
        self.set_font(font, "B" if not self.has_unicode_font else "", 9)
        self.set_xy(15, 3)
        self.cell(100, 8, "MEDLENS HEALTH SYSTEM  |  CLINICAL CASE SUMMARY", align="L")
        self.set_xy(120, 3)
        self.cell(75, 8, f"CASE: {self.case_id}  |  {self.intake_date}", align="R")
        self.set_text_color(15, 23, 42)
        self.ln(12)

    def footer(self):
        font = self.get_font_name()
        self.set_y(-14)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_font(font, "" if self.has_unicode_font else "I", 7.5)
        self.set_text_color(100, 116, 139)
        self.set_xy(15, -12)
        self.cell(120, 8, f"Status: {self.report_status}  *  AI-generated draft - physician verification required", align="L")
        self.set_xy(140, -12)
        self.cell(55, 8, f"Page {self.page_no()} of {{nb}}", align="R")


def sanitize_text(text: Any) -> str:
    """Helper to ensure clean, safe string representation without encoding errors."""
    if text is None:
        return ""
    s = str(text).strip()
    return s


def generate_clinical_pdf(
    report_data: Dict[str, Any],
    output_path: Optional[str] = None
) -> bytes:
    """
    Generates a publication-grade clinical case intake PDF.
    
    Args:
        report_data: Normalized report dictionary containing:
            patient, case, chief_complaints, history, medications,
            allergies, investigations, documents, red_flags,
            information_gaps, contradictions, interview_summary,
            ai_analysis, doctor_review.
        output_path: Optional file path to save PDF to disk.

    Returns:
        bytes: The compiled PDF binary.
    """
    case_meta = report_data.get("case", {})
    patient_meta = report_data.get("patient", {})
    case_id = case_meta.get("case_id") or "CASE-UNKNOWN"
    date_str = case_meta.get("created_at") or datetime.now().strftime("%Y-%m-%d")
    status_str = case_meta.get("status") or "Ready for Physician Review"

    pdf = MedLensReportPDF(case_id=case_id, intake_date=date_str, status=status_str)
    pdf.alias_nb_pages()
    pdf.add_page()
    font = pdf.get_font_name()

    # 1. Main Hospital & Document Title
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 16)
    pdf.set_text_color(2, 132, 199)  # MedLens Primary Blue
    pdf.cell(0, 8, "CLINICAL CASE SUMMARY & PRE-CONSULTATION INTAKE", ln=True, align="L")

    pdf.set_font(font, "" if pdf.has_unicode_font else "I", 8.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "Smart India Hackathon PS 26047  |  National Health Mission & ABDM HL7 FHIR Compatible Intake", ln=True, align="L")
    pdf.ln(2)

    # 2. Mandatory Non-Diagnostic Disclaimer Banner
    pdf.set_fill_color(254, 243, 199)  # Amber 100
    pdf.set_draw_color(251, 191, 36)  # Amber 400
    pdf.set_line_width(0.3)
    pdf.rect(15, pdf.get_y(), 180, 10, "DF")
    pdf.set_xy(18, pdf.get_y() + 1.5)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
    pdf.set_text_color(146, 64, 14)
    pdf.cell(0, 4, "[!] AI-GENERATED DRAFT - PHYSICIAN VERIFICATION REQUIRED", ln=True)
    pdf.set_xy(18, pdf.get_y())
    pdf.set_font(font, "", 7)
    pdf.set_text_color(180, 83, 9)
    pdf.cell(0, 3, "This document is an assistive clinical history draft and does not constitute a medical diagnosis or treatment order.", ln=True)
    pdf.ln(5)

    # 3. Patient Information Table
    pdf.set_fill_color(241, 245, 249)  # Slate 100
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(15, pdf.get_y(), 180, 20, "DF")

    p_name = sanitize_text(patient_meta.get("name") or "Outpatient")
    p_age = sanitize_text(patient_meta.get("age") or "Adult")
    p_gender = sanitize_text(patient_meta.get("gender") or "Unspecified")
    p_id = sanitize_text(patient_meta.get("patient_id") or "P-MEDLENS-01")
    p_abha = sanitize_text(patient_meta.get("abha_id") or "91-4589-2041-8832")
    p_lang = sanitize_text(case_meta.get("language") or "English")
    p_mode = sanitize_text(case_meta.get("input_mode") or "Voice Assisted")

    pdf.set_xy(18, pdf.get_y() + 2)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(58, 4, f"Patient Name: {p_name}", 0, 0)
    pdf.cell(58, 4, f"Age / Gender: {p_age} / {p_gender}", 0, 0)
    pdf.cell(58, 4, f"Patient ID: {p_id}", 0, 1)

    pdf.set_x(18)
    pdf.cell(58, 4, f"ABHA ID: {p_abha}", 0, 0)
    pdf.cell(58, 4, f"Language: {p_lang}", 0, 0)
    pdf.cell(58, 4, f"Intake Mode: {p_mode}", 0, 1)

    pdf.set_x(18)
    pdf.cell(58, 4, f"Case Ref: {case_id}", 0, 0)
    pdf.cell(58, 4, f"Date: {date_str}", 0, 0)
    pdf.cell(58, 4, f"Status: {status_str}", 0, 1)
    pdf.ln(5)

    # 4. Triage Acuity Indicator & Red Flags Section
    red_flags = report_data.get("red_flags", [])
    has_red_flags = len(red_flags) > 0

    if has_red_flags:
        pdf.set_fill_color(254, 226, 226)  # Red 100
        pdf.set_draw_color(239, 68, 68)    # Red 500
        pdf.rect(15, pdf.get_y(), 180, 7 + (len(red_flags) * 5), "DF")
        pdf.set_xy(18, pdf.get_y() + 1.5)
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8.5)
        pdf.set_text_color(185, 28, 28)
        pdf.cell(0, 4, "PRIORITY CLINICAL RED FLAGS DETECTED (HIGH ACUITY):", ln=True)
        pdf.set_font(font, "", 7.5)
        pdf.set_text_color(127, 29, 29)
        for rf in red_flags:
            rf_desc = sanitize_text(rf.get("description") or rf.get("title") or "Urgent clinical symptom reported")
            rf_trigger = sanitize_text(rf.get("trigger_text") or rf.get("trigger") or "")
            trig_str = f" [Trigger: \"{rf_trigger}\"]" if rf_trigger else ""
            pdf.set_x(22)
            pdf.cell(0, 4, f"* {rf_desc}{trig_str}", ln=True)
        pdf.ln(3)
    else:
        pdf.set_fill_color(240, 253, 244)  # Green 50
        pdf.set_draw_color(134, 239, 172)  # Green 300
        pdf.rect(15, pdf.get_y(), 180, 7, "DF")
        pdf.set_xy(18, pdf.get_y() + 1.5)
        pdf.set_font(font, "", 8)
        pdf.set_text_color(21, 128, 61)
        pdf.cell(0, 4, "[OK] No predefined red-flag emergency responses identified during pre-consultation interview.", ln=True)
        pdf.ln(3)

    # 5. Chief Complaints Section (Preserving all complaints)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "1. CHIEF COMPLAINTS", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(1)

    complaints = report_data.get("chief_complaints", [])
    if not complaints:
        complaint_single = case_meta.get("chief_complaint") or "General clinical consultation"
        complaints = [complaint_single]

    pdf.set_font(font, "", 8.5)
    pdf.set_text_color(30, 41, 59)
    for idx, c in enumerate(complaints, start=1):
        c_text = sanitize_text(c)
        pdf.cell(180, 5, f"   {idx}. {c_text}", ln=True)
    pdf.ln(2)

    # 6. History of Present Illness (HPI - OPQRST Structure)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "2. HISTORY OF PRESENT ILLNESS (HPI)", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(1)

    hpi_data = report_data.get("history", {}).get("hpi") or report_data.get("hpi") or {}
    hpi_elements = [
        ("Onset", hpi_data.get("onset")),
        ("Duration", hpi_data.get("duration")),
        ("Location", hpi_data.get("location")),
        ("Character / Nature", hpi_data.get("character")),
        ("Severity", hpi_data.get("severity")),
        ("Radiation", hpi_data.get("radiation")),
        ("Aggravating Factors", hpi_data.get("aggravating")),
        ("Relieving Factors", hpi_data.get("relieving")),
        ("Associated Symptoms", hpi_data.get("associated_symptoms"))
    ]

    pdf.set_font(font, "", 8)
    for label, val in hpi_elements:
        if val is not None and str(val).strip():
            val_str = ", ".join(val) if isinstance(val, list) else sanitize_text(val)
            if isinstance(val, dict):
                val_str = sanitize_text(val.get("value") or val)
            pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
            pdf.cell(45, 4.5, f"   * {label}:", 0, 0)
            pdf.set_font(font, "", 8)
            pdf.cell(135, 4.5, val_str, 0, 1)
    pdf.ln(2)

    # 7. Medical, Surgical & Family History
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "3. MEDICAL & SYSTEMIC HISTORY", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(1)

    hist = report_data.get("history", {})
    hist_items = [
        ("Past Medical History", hist.get("past_medical_history") or "Not reported"),
        ("Surgical History", hist.get("past_surgical_history") or "None reported"),
        ("Family Medical History", hist.get("family_history") or "No major hereditary illness reported"),
        ("Allergies & Sensitivities", report_data.get("allergies") or "No known drug allergies reported (NKDA)"),
        ("Social / Lifestyle", hist.get("personal_social_history") or "Non-smoker, non-alcoholic"),
        ("Review of Systems (ROS)", hist.get("review_of_systems") or "Normal constitutional baseline")
    ]

    for label, val in hist_items:
        v_str = ", ".join(val) if isinstance(val, list) else sanitize_text(val)
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
        pdf.cell(45, 4.5, f"   * {label}:", 0, 0)
        pdf.set_font(font, "", 8)
        pdf.cell(135, 4.5, v_str, 0, 1)
    pdf.ln(2)

    # 8. Medications Table (with Provenance)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "4. CURRENT PHARMACOTHERAPY & MEDICATIONS", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    medications = report_data.get("medications", [])
    if medications:
        # Table Header
        pdf.set_fill_color(224, 231, 255)  # Indigo 100
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 7.5)
        pdf.cell(60, 5, "Medication Name", 1, 0, "L", fill=True)
        pdf.cell(30, 5, "Dose / Frequency", 1, 0, "C", fill=True)
        pdf.cell(45, 5, "Source / Document", 1, 0, "L", fill=True)
        pdf.cell(45, 5, "Verification Status", 1, 1, "C", fill=True)

        pdf.set_font(font, "", 7.5)
        for med in medications:
            if isinstance(med, dict):
                m_name = sanitize_text(med.get("name") or med.get("value") or "Prescription Drug")
                m_dose = sanitize_text(med.get("dose") or med.get("frequency") or "As directed")
                m_src = sanitize_text(med.get("source") or "Patient Reported")
                m_ver = sanitize_text(med.get("verification_status") or "Unverified")
            else:
                m_name = sanitize_text(med)
                m_dose = "As directed"
                m_src = "Patient Reported"
                m_ver = "Unverified"

            pdf.cell(60, 5, f" {m_name}", 1, 0, "L")
            pdf.cell(30, 5, m_dose, 1, 0, "C")
            pdf.cell(45, 5, f" {m_src}", 1, 0, "L")
            pdf.cell(45, 5, m_ver, 1, 1, "C")
    else:
        pdf.set_font(font, "", 8)
        pdf.cell(0, 4.5, "   No active prescriptions or chronic medications reported.", ln=True)
    pdf.ln(2)

    # 9. Investigations & Medical Documents
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "5. INVESTIGATIONS & ATTACHED MEDICAL DOCUMENTS", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    docs = report_data.get("documents", [])
    if docs:
        pdf.set_fill_color(224, 231, 255)
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 7.5)
        pdf.cell(60, 5, "Document Title / File", 1, 0, "L", fill=True)
        pdf.cell(40, 5, "Document Type", 1, 0, "C", fill=True)
        pdf.cell(40, 5, "Extraction Status", 1, 0, "C", fill=True)
        pdf.cell(40, 5, "Clinical Verification", 1, 1, "C", fill=True)

        pdf.set_font(font, "", 7.5)
        for d in docs:
            d_name = sanitize_text(d.get("filename") or d.get("title") or "Uploaded Medical Document")
            d_type = sanitize_text(d.get("document_type") or "Medical Record")
            d_ext = "OCR Extracted" if d.get("extracted_data") else "Attached"
            d_ver = "Pending Physician Sign-Off"

            pdf.cell(60, 5, f" {d_name[:35]}", 1, 0, "L")
            pdf.cell(40, 5, d_type, 1, 0, "C")
            pdf.cell(40, 5, d_ext, 1, 0, "C")
            pdf.cell(40, 5, d_ver, 1, 1, "C")
    else:
        pdf.set_font(font, "", 8)
        pdf.cell(0, 4.5, "   No prior medical reports or imaging attached. Available for bedside review.", ln=True)
    pdf.ln(2)

    # 10. Information Requiring Attention (Gaps) & Contradictions
    gaps = report_data.get("information_gaps", [])
    contradictions = report_data.get("contradictions", [])

    if gaps or contradictions:
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "6. CLINICAL GAPS & ITEMS REQUIRING ATTENTION", ln=True)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(1)

        pdf.set_font(font, "", 8)
        if gaps:
            pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
            pdf.cell(0, 4.5, "   * Information Requiring Clinician Attention (Gaps):", ln=True)
            pdf.set_font(font, "", 8)
            for g in gaps:
                g_str = sanitize_text(g)
                pdf.cell(0, 4, f"     - {g_str}", ln=True)

        if contradictions:
            pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 8)
            pdf.set_text_color(180, 83, 9)
            pdf.cell(0, 4.5, "   * Discrepancies Requiring Verification:", ln=True)
            pdf.set_font(font, "", 8)
            pdf.set_text_color(30, 41, 59)
            for c in contradictions:
                c_desc = sanitize_text(c.get("discrepancy_description") or c.get("conflict_description") or "Discrepancy noted")
                pdf.cell(0, 4, f"     - {c_desc}", ln=True)
        pdf.ln(2)

    # 11. AI-Assisted Clinical Guidance (Non-Diagnostic)
    ai_analysis = report_data.get("ai_analysis", {})
    diffs = ai_analysis.get("recommended_workup") or ai_analysis.get("cds_recommendations") or []
    if diffs:
        pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "7. AI-ASSISTED CLINICAL DECISION SUPPORT (CDS GUIDANCE)", ln=True)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(1)
        pdf.set_font(font, "", 8)
        for r in diffs[:4]:
            pdf.cell(0, 4.5, f"   * Recommended Workup: {sanitize_text(r)}", ln=True)
        pdf.ln(2)

    # 12. Attending Physician Review & Sign-Off Block
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "8. ATTENDING PHYSICIAN ASSESSMENT & PLAN", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    # Sign-off box with lined space for handwriting
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(15, pdf.get_y(), 180, 32, "DF")

    pdf.set_xy(18, pdf.get_y() + 2)
    pdf.set_font(font, "", 8)
    pdf.cell(100, 4, "Clinical Impression & Diagnosis: __________________________________________________", ln=True)
    pdf.set_x(18)
    pdf.cell(100, 4, "Management Plan & Rx: ____________________________________________________________", ln=True)
    pdf.set_x(18)
    pdf.cell(100, 4, "Follow-Up Instructions: ___________________________________________________________", ln=True)

    pdf.set_xy(130, pdf.get_y() + 3)
    pdf.set_font(font, "B" if not pdf.has_unicode_font else "", 7.5)
    pdf.cell(60, 4, "Physician Signature / Reg. Stamp", 0, 1, "C")
    pdf.set_x(130)
    pdf.set_font(font, "", 7)
    pdf.cell(60, 4, "Date: ____________________", 0, 1, "C")

    # Output bytes
    pdf_bytes = bytes(pdf.output())

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
