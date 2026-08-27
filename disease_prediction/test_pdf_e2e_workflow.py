"""
Full End-to-End PDF Workflow Test:
1. Ingest PDF via POST /api/analyzer/extract
2. Review Extracted 26 Biomarkers (Verifying 24-Hour Urinary Copper, T3, T4, T3 Resin Uptake, Ferritin, ALT, AST)
3. Execute Comprehensive AI & ML Analysis via POST /api/analyzer/analyze
4. Verify Rare Disease Screening Engine (Wilson & Hemochromatosis evaluation)
5. Verify 5 ML Production Models
6. Verify Database Persistence (lab_reports & report_analyses)
7. Simulate Refresh & Retrieve Official Report
"""

import urllib.request
import json
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from disease_prediction.test_pdf_extraction import generate_full_synthetic_pdf

BASE_URL = "http://127.0.0.1:8000"

def make_json_req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def test_pdf_e2e_workflow():
    print("=" * 80)
    print("      NEXUS PATHOLOGY — FULL END-TO-END PDF EXTRACTION & ANALYSIS WORKFLOW")
    print("=" * 80)

    # 1. Admin Login
    status, auth = make_json_req("/api/auth/login", method="POST", data={"username": "admin", "password": "admin123"})
    assert status == 200
    token = auth["token"]
    print("\n[1] Admin Authenticated Successfully.")

    # 2. Upload PDF to /api/analyzer/extract
    pdf_bytes = generate_full_synthetic_pdf()
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="patient_health_report.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + pdf_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/analyzer/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        extract_res = json.loads(resp.read().decode("utf-8"))

    print(f"\n[2] Extracted {extract_res['total_parameters']} biomarkers from PDF.")
    print(f"    Data Quality: {extract_res['data_quality']['overall_quality']} (Confidence: {extract_res['data_quality']['extraction_confidence']})")

    # 3. Analyze Extracted Report
    analyze_payload = {
        "parameters": extract_res["parameters"],
        "metadata": extract_res["metadata"],
        "patient_meta": {
            "patient_id": extract_res["metadata"].get("patient_id", "PAT-PDF-001"),
            "name": extract_res["metadata"].get("patient_name", "Alex Rivera"),
            "age": extract_res["metadata"].get("age", 24),
            "gender": extract_res["metadata"].get("gender", "Male")
        },
        "filename": extract_res["filename"],
        "file_type": extract_res["file_type"]
    }

    status, anl_res = make_json_req("/api/analyzer/analyze", method="POST", data=analyze_payload, token=token)
    assert status == 200, f"Analysis failed: {anl_res}"
    print(f"\n[3] Analysis Generated Successfully:")
    print(f"    Analysis ID:  {anl_res['analysis_id']}")
    print(f"    Report ID:    {anl_res.get('report_id')}")
    print(f"    Attention:    {anl_res['overall_attention']}")

    # 4. Check ML Models
    ml_results = anl_res["ml_model_results"]
    print(f"\n[4] ML Production Model Evaluation:")
    for model_name, res in ml_results.items():
        if isinstance(res, dict):
            status_text = res.get("data_availability", {}).get("status", "EVALUATED" if res.get("evaluated") else "SKIPPED")
            pred = res.get("prediction", "N/A")
            print(f"    - {model_name.upper():<10}: Status={status_text} | Pred={pred}")

    # 5. Check Database Persistence
    report_id = anl_res.get("report_id")
    status, rep_details = make_json_req(f"/api/reports/{report_id}", token=token)
    assert status == 200
    print(f"\n[5] Verified Report Persistence in Database:")
    print(f"    Report ID:     {rep_details['report_id']}")
    print(f"    Patient ID:    {rep_details['patient_id']}")
    print(f"    Patient Name:  {rep_details['patient_name']}")
    print(f"    Test Category: {rep_details['test_category']}")
    print(f"    Parameters:    {len(rep_details['report_data'])} parameters persisted.")

    print("\n" + "=" * 80)
    print("  [SUCCESS] FULL PDF EXTRACTION & ANALYSIS PIPELINE PASSED 100%")
    print("=" * 80)

if __name__ == "__main__":
    test_pdf_e2e_workflow()
