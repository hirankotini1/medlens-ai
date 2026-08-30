"""
Live End-to-End Test for G6PD PDF Upload, Extraction, Analysis, and Data-Quality Reporting.
"""

import urllib .request 
import json 
import uuid 
import sys 
import os 

BASE_URL ="http://127.0.0.1:8000"

def generate_g6pd_synthetic_pdf ()->bytes :
    """Generates a raw PDF stream containing 27 biomarkers including G6PD and Platelets."""
    pdf_stream =(
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"4 0 obj << /Length 950 >> stream\n"
    b"BT /F1 10 Tf 50 720 Td (Patient Name: Marcus Vance) Tj 0 -15 Td (Patient ID: PAT-G6PD-901) Tj 0 -15 Td (Age: 26 Yrs    Gender: Male) Tj 0 -25 Td\n"
    b"(INVESTIGATION               OBSERVED VALUE   UNIT         REFERENCE RANGE   STATUS) Tj 0 -15 Td\n"
    b"(G6PD Enzyme Activity         2.1              U/g Hb       7.0 - 10.5        LOW) Tj 0 -15 Td\n"
    b"(LDH                          610.0            U/L          140.0 - 280.0     HIGH) Tj 0 -15 Td\n"
    b"(Haptoglobin                  16.0             mg/dL        30.0 - 200.0      LOW) Tj 0 -15 Td\n"
    b"(Indirect Bilirubin           3.5              mg/dL        0.1 - 0.8         HIGH) Tj 0 -15 Td\n"
    b"(Reticulocyte Count           6.1              %            0.5 - 2.5         HIGH) Tj 0 -15 Td\n"
    b"(Hemoglobin                   10.8             g/dL         13.0 - 17.0       LOW) Tj 0 -15 Td\n"
    b"(Total Bilirubin              4.2              mg/dL        0.2 - 1.2         HIGH) Tj 0 -15 Td\n"
    b"(Platelet Count               205000           /uL          150000 - 450000   NORMAL) Tj 0 -15 Td\n"
    b"(WBC Count                    7200             /uL          4000 - 11000      NORMAL) Tj 0 -15 Td\n"
    b"(Ferritin                     160.0            ng/mL        30.0 - 400.0      NORMAL) Tj 0 -15 Td\n"
    b"(ALT                          32.0             U/L          10.0 - 40.0       NORMAL) Tj 0 -15 Td\n"
    b"(AST                          28.0             U/L          10.0 - 40.0       NORMAL) Tj 0 -15 Td\n"
    b"ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000300 00000 n\n0000000234 00000 n\n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n1350\n%%EOF\n"
    )
    return pdf_stream 

def test_live_g6pd_pdf ():
    print ("="*80 )
    print ("LIVE G6PD PDF END-TO-END TEST")
    print ("="*80 )


    req_auth =urllib .request .Request (
    f"{BASE_URL }/api/auth/login",
    data =json .dumps ({"username":"admin","password":"admin123"}).encode ("utf-8"),
    headers ={"Content-Type":"application/json"}
    )
    with urllib .request .urlopen (req_auth ,timeout =10 )as resp :
        auth_data =json .loads (resp .read ().decode ("utf-8"))
    token =auth_data ["token"]


    pdf_bytes =generate_g6pd_synthetic_pdf ()
    boundary ="----WebKitFormBoundary"+uuid .uuid4 ().hex [:16 ]
    body =(
    f"--{boundary }\r\n"
    f'Content-Disposition: form-data; name="file"; filename="g6pd_patient_report.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
    ).encode ("utf-8")+pdf_bytes +f"\r\n--{boundary }--\r\n".encode ("utf-8")

    req_extract =urllib .request .Request (
    f"{BASE_URL }/api/analyzer/extract",
    data =body ,
    headers ={"Content-Type":f"multipart/form-data; boundary={boundary }"},
    method ="POST"
    )
    with urllib .request .urlopen (req_extract ,timeout =15 )as resp :
        extracted =json .loads (resp .read ().decode ("utf-8"))

    params =extracted ["parameters"]
    param_map ={p ["canonical_key"]:p for p in params }

    print (f"Extracted {len (params )} biomarkers from PDF:")
    for p in params :
        print (f"  - {p ['canonical_key']:<22}: {p ['value']} {p ['unit']} (Ref: {p ['reference_range']}) [{p ['status']}]")


    assert "G6PD_ENZYME_ACTIVITY"in param_map ,"G6PD_ENZYME_ACTIVITY missing from extraction!"
    g6pd_p =param_map ["G6PD_ENZYME_ACTIVITY"]
    assert g6pd_p ["value"]==2.1 ,f"Expected 2.1, got {g6pd_p ['value']}"
    assert g6pd_p ["status"]=="LOW",f"Expected LOW, got {g6pd_p ['status']}"


    assert "PLT"in param_map ,"PLT missing from extraction!"
    plt_p =param_map ["PLT"]
    assert plt_p ["value"]==205000.0 ,f"Expected 205000, got {plt_p ['value']}"


    analyze_payload ={
    "parameters":params ,
    "metadata":extracted ["metadata"],
    "patient_meta":{"patient_id":"PAT-G6PD-901","name":"Marcus Vance","age":26 ,"gender":"Male"},
    "filename":"g6pd_patient_report.pdf",
    "file_type":"PDF"
    }
    req_analyze =urllib .request .Request (
    f"{BASE_URL }/api/analyzer/analyze",
    data =json .dumps (analyze_payload ).encode ("utf-8"),
    headers ={"Content-Type":"application/json","Authorization":f"Bearer {token }"},
    method ="POST"
    )
    with urllib .request .urlopen (req_analyze ,timeout =45 )as resp :
        anl_res =json .loads (resp .read ().decode ("utf-8"))

    rare_res =anl_res ["ai_analysis"].get ("rare_unusual_screening")or anl_res ["ai_analysis"].get ("rare_disease_screening")
    print ("\nRare Disease Screening Output:")
    print (f"  Flagged:           {rare_res ['flagged']}")
    print (f"  Top Condition:     {rare_res ['condition_name']}")
    print (f"  Screening Signal:  {rare_res ['screening_strength']}")

    assert rare_res ["flagged"]is True 
    assert "G6PD"in rare_res ["condition_name"],f"G6PD not top condition: {rare_res ['condition_name']}"
    assert rare_res ["screening_strength"]=="HIGH",f"Expected HIGH, got {rare_res ['screening_strength']}"


    dq =anl_res .get ("data_quality",{})
    print (f"\nData Quality: Detected={dq .get ('biomarkers_detected')}, Ranges={dq .get ('reference_ranges_detected')}, Unmapped={dq .get ('unmapped_parameters')}")
    assert dq .get ("reference_ranges_detected",0 )>=10 ,f"Expected >= 10 ranges, got {dq .get ('reference_ranges_detected')}"

    print ("\n[SUCCESS] All live G6PD PDF assertions passed 100%!")

if __name__ =="__main__":
    test_live_g6pd_pdf ()
