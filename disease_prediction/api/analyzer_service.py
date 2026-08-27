"""
MEDLENS — AI Health Report Analyzer Service Coordinator
Orchestrates file ingestion, parameter extraction, metadata separation, user review preparation,
OpenRouter AI decision support, and existing ML model execution.
"""

from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .file_parser import validate_file_metadata, parse_csv_report, parse_pdf_report, parse_image_report
from .report_extractor import (
    extract_metadata_and_biomarkers,
    extract_parameters_from_raw_items,
    extract_parameters_from_text,
    calculate_report_data_quality,
    normalize_param_name
)
from .openrouter_service import analyze_report_with_ai
from .ml_bridge import evaluate_extracted_report_with_ml


def extract_report_from_file_bytes(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Validates and extracts structured laboratory parameters and metadata from uploaded file bytes.
    Cleanly separates patient/report metadata from clinical biomarkers.
    Prepares data for user review and interactive editing before final analysis.
    """
    ext = validate_file_metadata(filename, file_bytes)
    extracted_params: List[Dict[str, Any]] = []
    extracted_metadata: Dict[str, Any] = {}
    raw_text = ""
    preview_image_url = None

    if ext == ".csv":
        extracted_metadata, raw_items = parse_csv_report(file_bytes)
        extracted_params = extract_parameters_from_raw_items(raw_items)
    elif ext == ".pdf":
        raw_text, _ = parse_pdf_report(file_bytes)
        extracted_metadata, extracted_params = extract_metadata_and_biomarkers(raw_text)
    elif ext in [".jpg", ".jpeg", ".png"]:
        preview_image_url, raw_text = parse_image_report(file_bytes, filename)
        extracted_metadata, extracted_params = extract_metadata_and_biomarkers(raw_text)
    elif ext == ".txt":
        raw_text = file_bytes.decode("utf-8", errors="replace")
        extracted_metadata, extracted_params = extract_metadata_and_biomarkers(raw_text)

    abnormal_count = sum(
        1 for p in extracted_params
        if str(p.get("status", "")).upper() in ["LOW", "HIGH", "CRITICAL", "CRITICAL LOW", "CRITICAL HIGH"]
    )

    data_quality = calculate_report_data_quality(extracted_metadata, extracted_params)

    # Structured Debug Logging (Without logging patient PII or API credentials)
    total_lines = len([l for l in raw_text.splitlines() if l.strip()]) if raw_text else len(extracted_params)
    print("=" * 60)
    print(f"[EXTRACTION-AUDIT] Report Ingested: {filename} (Format: {ext.replace('.', '').upper()})")
    print(f"[EXTRACTION-AUDIT] Raw document text length: {len(raw_text)} chars")
    print(f"[EXTRACTION-AUDIT] Table rows / text lines detected: {total_lines}")
    print(f"[EXTRACTION-AUDIT] Biomarkers parsed: {len(extracted_params)}")
    print(f"[EXTRACTION-AUDIT] Extraction confidence: {data_quality.get('extraction_confidence')}")
    print(f"[EXTRACTION-AUDIT] Overall quality: {data_quality.get('overall_quality')}")
    print("=" * 60)

    return {
        "filename": filename,
        "file_type": ext.replace(".", "").upper(),
        "file_size_kb": round(len(file_bytes) / 1024, 1),
        "metadata": extracted_metadata,
        "parameters": extracted_params,
        "total_parameters": len(extracted_params),
        "abnormal_count": abnormal_count,
        "preview_image_url": preview_image_url,
        "raw_text_extracted": bool(raw_text.strip()),
        "data_quality": data_quality
    }


def perform_comprehensive_analysis(
    parameters: List[Dict[str, Any]], 
    patient_meta: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    image_b64: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes full multi-tier analysis:
    Tier 1: OpenRouter AI Clinical Decision Support
    Tier 2: Validated Production ML Models (Anemia, Dengue, Liver, Thyroid)
    Tier 3: Visual Health Summary Assembly
    """
    if not parameters:
        raise ValueError("Cannot perform analysis on empty parameter list. Please provide at least one laboratory value.")

    # Combine document metadata with session patient_meta
    merged_meta: Dict[str, Any] = {}
    if metadata:
        merged_meta.update(metadata)
    if patient_meta:
        merged_meta.update(patient_meta)

    # Invariant: Guarantee all recognized parameters retain their canonical_key
    enriched_parameters = []
    for p in parameters:
        p_dict = dict(p)
        if not p_dict.get("canonical_key") or p_dict.get("canonical_key") == "UNKNOWN":
            c_key, norm_meta = normalize_param_name(str(p_dict.get("parameter", "")))
            if c_key:
                p_dict["canonical_key"] = c_key
                if not p_dict.get("normalized_name"):
                    p_dict["normalized_name"] = norm_meta["name"] if norm_meta else p_dict.get("parameter")
        enriched_parameters.append(p_dict)
    parameters = enriched_parameters

    # Run OpenRouter AI analysis and ML model bridge CONCURRENTLY for maximum speed
    ai_result: Dict[str, Any] = {}
    ml_results: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_ai = executor.submit(
            analyze_report_with_ai, parameters, merged_meta, image_b64
        )
        future_ml = executor.submit(
            evaluate_extracted_report_with_ml, parameters, merged_meta
        )
        # Collect results as they complete (AI is slower, so grab it when ready)
        for future in as_completed([future_ai, future_ml]):
            if future is future_ai:
                try:
                    ai_result = future.result()
                except Exception as e:
                    ai_result = {"overall_attention": "NORMAL", "summary": f"AI analysis unavailable: {e}",
                                 "abnormal_findings": [], "patterns": [], "general_precautions": [],
                                 "rare_unusual_screening": {"flagged": False}}
            else:
                try:
                    ml_results = future.result()
                except Exception as e:
                    ml_results = {}

    # Synthesis: escalate attention level if ML finds high risk
    overall_attention = ai_result.get("overall_attention", "NORMAL")
    has_high_ml_risk = any(
        res.get("risk_level") == "High"
        for res in ml_results.values()
        if isinstance(res, dict) and res.get("evaluated")
    )
    if has_high_ml_risk and overall_attention == "NORMAL":
        overall_attention = "MODERATE ATTENTION"

    data_quality = calculate_report_data_quality(merged_meta, parameters)

    return {
        "overall_attention": overall_attention,
        "metadata": merged_meta,
        "ai_analysis": ai_result,
        "ml_model_results": ml_results,
        "reviewed_parameters": parameters,
        "total_parameters_analyzed": len(parameters),
        "data_quality": data_quality
    }
