"""
Test script verifying the datetime NameError fix and Alpha-1 Antitrypsin Deficiency PDF workflow:
1. Add new patient
2. Generate and upload Alpha-1 Antitrypsin Deficiency PDF
3. Extract biomarkers
4. Run AI & Clinical ML Analysis
5. Verify zero datetime NameError
6. Verify report persistence in SQLite
7. Simulate page refresh & re-retrieve report
8. Re-run analysis
"""

import urllib.request
import json
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:8000"

def generate_aatd_pdf() -> bytes:
    stream_content = """
BT
/F1 10 Tf
50 720 Td
(Patient Name: Marcus Sterling) Tj
0 -15 Td
(Patient ID: PAT-AATD-001) Tj
0 -15 Td
(Age: 38 Yrs    Gender: Male) Tj
0 -15 Td
(Report ID: REP-2026-AATD-01) Tj
0 -25 Td
(==========================================================================) Tj
0 -15 Td
(INVESTIGATION               OBSERVED VALUE   UNIT         REFERENCE RANGE   STATUS) Tj
0 -15 Td
(==========================================================================) Tj
0 -15 Td
(Alpha-1 Antitrypsin) Tj
0 -15 Td
(ALT) Tj
0 -15 Td
(AST) Tj
0 -15 Td
(Total Bilirubin) Tj
0 -15 Td
(Albumin) Tj
0 -15 Td
(Total Protein) Tj
0 -15 Td
(Hemoglobin) Tj
0 -15 Td
(WBC Count) Tj
0 -15 Td
(Platelet Count) Tj
ET
BT
/F1 10 Tf
220 605 Td
(42.0) Tj
0 -15 Td
(88) Tj
0 -15 Td
(76) Tj
0 -15 Td
(1.8) Tj
0 -15 Td
(3.2) Tj
0 -15 Td
(6.8) Tj
0 -15 Td
(14.2) Tj
0 -15 Td
(6400) Tj
0 -15 Td
(210000) Tj
ET
BT
/F1 10 Tf
290 605 Td
(mg/dL) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(mg/dL) Tj
0 -15 Td
(g/dL) Tj
0 -15 Td
(g/dL) Tj
0 -15 Td
(g/dL) Tj
0 -15 Td
(/uL) Tj
0 -15 Td
(/uL) Tj
ET
BT
/F1 10 Tf
370 605 Td
(90.0-200.0) Tj
0 -15 Td
(10-40) Tj
0 -15 Td
(10-40) Tj
0 -15 Td
(0.2-1.2) Tj
0 -15 Td
(3.5-5.0) Tj
0 -15 Td
(6.0-8.3) Tj
0 -15 Td
(13.0-17.0) Tj
0 -15 Td
(4000-11000) Tj
0 -15 Td
(150000-450000) Tj
ET
"""
    stream_bytes = stream_content.encode("latin1")
    pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(stream_bytes)} >>
stream
{stream_content}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000242 00000 n 
0000000{242 + len(stream_bytes) + 40:03d} 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
{242 + len(stream_bytes) + 120}
%%EOF"""
    return pdf_template.encode("latin1")

def make_json_req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def test_full_workflow():
    print("=" * 80)
    print("      NEXUS PATHOLOGY — DATETIME FIX & AATD PDF VERIFICATION")
    print("=" * 80)

    # 1. Admin Authentication
    status, auth = make_json_req("/api/auth/login", method="POST", data={"username": "admin", "password": "admin123"})
    assert status == 200, f"Admin login failed: {auth}"
    admin_token = auth["token"]
    print("\n[STEP 1] Admin Authenticated.")

    # 2. Add New Patient
    pat_payload = {
        "patient_id": "PAT-AATD-001",
        "name": "Marcus Sterling",
        "age": 38,
        "gender": "Male",
        "contact": "+1-555-0199",
        "email": "marcus.s@example.com",
        "access_pin": "PIN-9999"
    }
    status, pat_res = make_json_req("/api/patients", method="POST", data=pat_payload, token=admin_token)
    assert status == 200, f"Patient creation failed: {pat_res}"
    print(f"[STEP 2] Registered Patient: {pat_res['patient_id']} ({pat_res['name']})")

    # 3. Ingest Alpha-1 Antitrypsin PDF
    pdf_bytes = generate_aatd_pdf()
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="Alpha1_Antitrypsin_Report.pdf"\r\n'
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

    assert resp.status == 200, f"PDF Extraction failed: {extract_res}"
    print(f"[STEP 3] PDF Extracted: {extract_res['total_parameters']} biomarkers found.")
    
    # Audit extracted Alpha-1 Antitrypsin
    param_map = {p["parameter"]: p for p in extract_res["parameters"]}
    assert "Alpha-1 Antitrypsin" in param_map, "Alpha-1 Antitrypsin not found in extracted parameters!"
    aat_p = param_map["Alpha-1 Antitrypsin"]
    assert aat_p["value"] == 42.0, f"Expected 42.0, got {aat_p['value']}"
    assert "mg/dL" in aat_p["unit"]
    assert aat_p["status"] == "LOW"
    print(f"  [PASS] Alpha-1 Antitrypsin = {aat_p['value']} {aat_p['unit']} ({aat_p['status']})")

    # 4. Run AI & Clinical ML Analysis
    analyze_payload = {
        "parameters": extract_res["parameters"],
        "metadata": extract_res["metadata"],
        "patient_meta": {
            "patient_id": "PAT-AATD-001",
            "name": "Marcus Sterling",
            "age": 38,
            "gender": "Male"
        },
        "filename": "Alpha1_Antitrypsin_Report.pdf",
        "file_type": "PDF"
    }

    status, anl_res = make_json_req("/api/analyzer/analyze", method="POST", data=analyze_payload, token=admin_token)
    assert status == 200, f"Analysis failed: {anl_res}"
    print(f"[STEP 4] AI & ML Analysis Generated Without Error!")
    print(f"  Analysis ID: {anl_res['analysis_id']}")
    print(f"  Report ID:   {anl_res.get('report_id')}")
    print(f"  Attention:   {anl_res['overall_attention']}")

    # Check Rare Disease Screening for AATD
    ai_analysis = anl_res.get("ai_analysis", {})
    rare_screening = ai_analysis.get("rare_unusual_screening", {})
    print(f"  Rare Disease Signal: {rare_screening.get('condition_name')} (Strength: {rare_screening.get('screening_strength')})")
    assert rare_screening.get("flagged") is True, "Expected rare disease screening to flag AATD pattern!"

    # 5. Verify Persistence in SQLite
    report_id = anl_res.get("report_id")
    status, rep_details = make_json_req(f"/api/reports/{report_id}", token=admin_token)
    assert status == 200
    assert rep_details["patient_id"] == "PAT-AATD-001"
    print(f"[STEP 5] Verified Report Persistence: {rep_details['report_id']} saved for {rep_details['patient_name']}.")

    # 6. Simulate Browser Refresh & Patient Portal Login
    status, pat_login = make_json_req("/api/patient/login", method="POST", data={"patient_id": "PAT-AATD-001", "access_pin": "PIN-9999"})
    assert status == 200, f"Patient portal login failed: {pat_login}"
    pat_token = pat_login["token"]
    status, pat_reports = make_json_req("/api/reports?patient_id=PAT-AATD-001", token=pat_token)
    assert status == 200
    assert len(pat_reports) >= 1
    print(f"[STEP 6] Patient Portal Verified: Retrieved {len(pat_reports)} isolated reports for PAT-AATD-001.")

    # 7. Re-run Analysis
    status, re_anl_res = make_json_req("/api/analyzer/analyze", method="POST", data=analyze_payload, token=admin_token)
    assert status == 200, f"Re-analysis failed: {re_anl_res}"
    print(f"[STEP 7] Re-analysis Succeeded Cleanly: Analysis ID {re_anl_res['analysis_id']}")

    print("\n" + "=" * 80)
    print("  [SUCCESS] ALL DATETIME FIX & AATD PDF WORKFLOW CHECKS PASSED 100%")
    print("=" * 80)

if __name__ == "__main__":
    test_full_workflow()
