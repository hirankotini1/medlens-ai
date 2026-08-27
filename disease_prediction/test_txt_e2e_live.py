"""
Live HTTP End-to-End Test for G6PD TXT Report Upload, Ingestion, Review, and Analysis.
"""

import urllib.request
import json
import uuid
import sys
import os

BASE_URL = "http://127.0.0.1:8000"

SAMPLE_TXT = """
========================================================================================
                      NEXUS PATHOLOGY LABORATORY SERVICES
========================================================================================
Patient ID = RARE-TEST-007
Patient Name = Synthetic Rare Disease Test
Age = 26
Gender = Male
Report ID = NEXUS-RARE-007
Report Date = 27-Aug-2026

INVESTIGATION                  VALUE    UNIT         REFERENCE RANGE   STATUS
----------------------------------------------------------------------------------------
G6PD Enzyme Activity = 2.1 U/g Hb
Reference Range = 7.0–10.5
Status = LOW

Platelet Count = 205000 /uL
Reference Range = 150000-450000
Status = NORMAL

LDH = 610 U/L
Reference Range = 140-280
Status = HIGH

Haptoglobin = 16 mg/dL
Reference Range = 30-200
Status = LOW

Indirect Bilirubin = 3.5 mg/dL
Reference Range = 0.1-0.8
Status = HIGH

Reticulocyte Count = 6.1 %
Reference Range = 0.5-2.5
Status = HIGH

Hemoglobin = 10.8 g/dL
Reference Range = 12.0-16.0
Status = LOW

Total Bilirubin = 4.2 mg/dL
Reference Range = 0.2-1.2
Status = HIGH

WBC Count = 7200 /uL
Reference Range = 4000-11000
Status = NORMAL

Ferritin = 180 ng/mL
Reference Range = 30-400
Status = NORMAL

ALT = 34 U/L
Reference Range = 10-40
Status = NORMAL

AST = 29 U/L
Reference Range = 10-40
Status = NORMAL
========================================================================================
"""

def test_live_txt_flow():
    print("=" * 80)
    print("LIVE G6PD TXT END-TO-END WORKFLOW TEST")
    print("=" * 80)

    # 1. Login
    req_auth = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_auth, timeout=10) as resp:
        auth_data = json.loads(resp.read().decode("utf-8"))
    token = auth_data["token"]

    # 2. Upload TXT to /api/analyzer/extract
    txt_bytes = SAMPLE_TXT.encode("utf-8")
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="G6PD_Deficiency_Rare_Disease_Test.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8") + txt_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req_extract = urllib.request.Request(
        f"{BASE_URL}/api/analyzer/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_extract, timeout=15) as resp:
        extracted = json.loads(resp.read().decode("utf-8"))

    meta = extracted["metadata"]
    params = extracted["parameters"]
    param_map = {p["canonical_key"]: p for p in params}

    print("\n1. Extracted Metadata:")
    print(f"  Patient ID:   {meta.get('patient_id')}")
    print(f"  Patient Name: {meta.get('patient_name')}")
    print(f"  Age:          {meta.get('age')}")
    print(f"  Gender:       {meta.get('gender')}")
    print(f"  Report ID:    {meta.get('report_id')}")
    print(f"  Report Date:  {meta.get('report_date')}")

    assert meta.get("patient_id") == "RARE-TEST-007", f"Expected RARE-TEST-007, got {meta.get('patient_id')}"
    assert meta.get("age") == 26, f"Expected 26, got {meta.get('age')}"
    assert meta.get("gender") == "Male", f"Expected Male, got {meta.get('gender')}"

    print(f"\n2. Extracted {len(params)} biomarkers from TXT:")
    for p in params:
        print(f"  - {p['canonical_key']:<22}: {p['value']} {p['unit']} (Ref: {p['reference_range']}) [{p['status']}]")

    # Verify G6PD extraction
    assert "G6PD_ENZYME_ACTIVITY" in param_map, "G6PD_ENZYME_ACTIVITY missing from extraction!"
    g6pd_p = param_map["G6PD_ENZYME_ACTIVITY"]
    assert g6pd_p["value"] == 2.1, f"Expected 2.1, got {g6pd_p['value']}"
    assert g6pd_p["status"] == "LOW", f"Expected LOW, got {g6pd_p['status']}"

    # Verify Platelet count value
    assert "PLT" in param_map, "PLT missing from extraction!"
    plt_p = param_map["PLT"]
    assert plt_p["value"] == 205000.0, f"Expected 205000, got {plt_p['value']}"

    # 3. Analyze (Simulating user review editor submission where canonical_key might be omitted)
    review_params = [
        {
            "parameter": p["parameter"],
            "canonical_key": p.get("canonical_key", ""),
            "value": p["value"],
            "unit": p["unit"],
            "reference_range": p["reference_range"],
            "status": p["status"]
        }
        for p in params
    ]

    analyze_payload = {
        "parameters": review_params,
        "metadata": meta,
        "patient_meta": {
            "patient_id": meta.get("patient_id") or "DEMO-001",
            "name": meta.get("patient_name") or "",
            "age": meta.get("age") or 32,
            "gender": meta.get("gender") or "Female"
        },
        "filename": "G6PD_Deficiency_Rare_Disease_Test.txt",
        "file_type": "TXT"
    }

    req_analyze = urllib.request.Request(
        f"{BASE_URL}/api/analyzer/analyze",
        data=json.dumps(analyze_payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    with urllib.request.urlopen(req_analyze, timeout=30) as resp:
        anl_res = json.loads(resp.read().decode("utf-8"))

    rare_res = anl_res["ai_analysis"].get("rare_unusual_screening") or anl_res["ai_analysis"].get("rare_disease_screening")
    print("\n3. Rare Disease Screening Output:")
    print(f"  Flagged:           {rare_res['flagged']}")
    print(f"  Top Condition:     {rare_res['condition_name']}")
    print(f"  Screening Signal:  {rare_res['screening_strength']}")

    assert rare_res["flagged"] is True
    assert "G6PD" in rare_res["condition_name"], f"G6PD not top condition: {rare_res['condition_name']}"
    assert rare_res["screening_strength"] == "HIGH", f"Expected HIGH, got {rare_res['screening_strength']}"

    # Verify Data Quality metrics in analysis response
    dq = anl_res.get("data_quality", {})
    print(f"\n4. Data Quality: Detected={dq.get('biomarkers_detected')}, Ranges={dq.get('reference_ranges_detected')}, Unmapped={dq.get('unmapped_parameters')}")
    assert dq.get("unmapped_parameters") == 0, f"Expected unmapped=0, got {dq.get('unmapped_parameters')}"
    assert dq.get("reference_ranges_detected", 0) >= 10, f"Expected >= 10 ranges, got {dq.get('reference_ranges_detected')}"

    print("\n[SUCCESS] All live G6PD TXT assertions passed 100%!")


if __name__ == "__main__":
    test_live_txt_flow()
