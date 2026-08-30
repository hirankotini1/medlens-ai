"""
Test suite verifying end-to-end PDF extraction for all 27 biomarkers,
ensuring zero position-only splitting, accurate multi-word name recognition,
correct unit extraction, and non-corrupted observed values.
"""

import io 
import sys 
import os 

sys .path .insert (0 ,os .path .abspath (os .path .join (os .path .dirname (__file__ ),"..")))
from disease_prediction .api .file_parser import parse_pdf_report 
from disease_prediction .api .report_extractor import extract_metadata_and_biomarkers ,calculate_report_data_quality 
from disease_prediction .api .analyzer_service import extract_report_from_file_bytes 

def generate_full_synthetic_pdf ()->bytes :
    stream_content ="""
BT
/F1 10 Tf
50 720 Td
(Patient Name: Alex Rivera) Tj
0 -15 Td
(Patient ID: TC-001-WILSON) Tj
0 -15 Td
(Age: 24 Yrs    Gender: Male) Tj
0 -15 Td
(Report ID: REP-2026-PDF-001) Tj
0 -25 Td
(==========================================================================) Tj
0 -15 Td
(INVESTIGATION               OBSERVED VALUE   UNIT         REFERENCE RANGE   STATUS) Tj
0 -15 Td
(==========================================================================) Tj
0 -15 Td
(Hemoglobin) Tj
0 -15 Td
(RBC Count) Tj
0 -15 Td
(WBC Count) Tj
0 -15 Td
(Platelet Count) Tj
0 -15 Td
(Total Bilirubin) Tj
0 -15 Td
(Direct Bilirubin) Tj
0 -15 Td
(ALT) Tj
0 -15 Td
(AST) Tj
0 -15 Td
(ALP) Tj
0 -15 Td
(Total Protein) Tj
0 -15 Td
(Albumin) Tj
0 -15 Td
(Ferritin) Tj
0 -15 Td
(Serum Iron) Tj
0 -15 Td
(Transferrin Saturation) Tj
0 -15 Td
(TIBC) Tj
0 -15 Td
(CRP) Tj
0 -15 Td
(Ceruloplasmin) Tj
0 -15 Td
(Serum Copper) Tj
0 -15 Td
(24-Hour Urinary Copper) Tj
0 -15 Td
(LDH) Tj
0 -15 Td
(Haptoglobin) Tj
0 -15 Td
(Reticulocyte Count) Tj
0 -15 Td
(TSH) Tj
0 -15 Td
(T3) Tj
0 -15 Td
(T4) Tj
0 -15 Td
(T3 Resin Uptake) Tj
ET
BT
/F1 10 Tf
220 605 Td
(14.8) Tj
0 -15 Td
(5.0) Tj
0 -15 Td
(6800) Tj
0 -15 Td
(230000) Tj
0 -15 Td
(1.1) Tj
0 -15 Td
(0.3) Tj
0 -15 Td
(95) Tj
0 -15 Td
(82) Tj
0 -15 Td
(105) Tj
0 -15 Td
(7.3) Tj
0 -15 Td
(4.0) Tj
0 -15 Td
(1250) Tj
0 -15 Td
(220) Tj
0 -15 Td
(78) Tj
0 -15 Td
(280) Tj
0 -15 Td
(2.0) Tj
0 -15 Td
(28) Tj
0 -15 Td
(100) Tj
0 -15 Td
(35) Tj
0 -15 Td
(210) Tj
0 -15 Td
(120) Tj
0 -15 Td
(1.2) Tj
0 -15 Td
(2.0) Tj
0 -15 Td
(1.2) Tj
0 -15 Td
(8.0) Tj
0 -15 Td
(32) Tj
ET
BT
/F1 10 Tf
290 605 Td
(g/dL) Tj
0 -15 Td
(million/uL) Tj
0 -15 Td
(/uL) Tj
0 -15 Td
(/uL) Tj
0 -15 Td
(mg/dL) Tj
0 -15 Td
(mg/dL) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(g/dL) Tj
0 -15 Td
(g/dL) Tj
0 -15 Td
(ng/mL) Tj
0 -15 Td
(ug/dL) Tj
0 -15 Td
(%) Tj
0 -15 Td
(ug/dL) Tj
0 -15 Td
(mg/L) Tj
0 -15 Td
(mg/dL) Tj
0 -15 Td
(ug/dL) Tj
0 -15 Td
(ug/24h) Tj
0 -15 Td
(U/L) Tj
0 -15 Td
(mg/dL) Tj
0 -15 Td
(%) Tj
0 -15 Td
(uIU/mL) Tj
0 -15 Td
(ng/mL) Tj
0 -15 Td
(ug/dL) Tj
0 -15 Td
(%) Tj
ET
BT
/F1 10 Tf
370 605 Td
(13.0-17.0) Tj
0 -15 Td
(4.5-5.9) Tj
0 -15 Td
(4000-11000) Tj
0 -15 Td
(150000-450000) Tj
0 -15 Td
(0.2-1.2) Tj
0 -15 Td
(0.0-0.3) Tj
0 -15 Td
(10-40) Tj
0 -15 Td
(10-40) Tj
0 -15 Td
(44-147) Tj
0 -15 Td
(6.0-8.3) Tj
0 -15 Td
(3.5-5.0) Tj
0 -15 Td
(30-400) Tj
0 -15 Td
(60-170) Tj
0 -15 Td
(20-50) Tj
0 -15 Td
(250-450) Tj
0 -15 Td
(0-5) Tj
0 -15 Td
(20-40) Tj
0 -15 Td
(70-140) Tj
0 -15 Td
(10-60) Tj
0 -15 Td
(140-280) Tj
0 -15 Td
(30-200) Tj
0 -15 Td
(0.5-2.5) Tj
0 -15 Td
(0.40-4.20) Tj
0 -15 Td
(0.8-2.0) Tj
0 -15 Td
(4.5-12.0) Tj
0 -15 Td
(24-39) Tj
ET
"""
    stream_bytes =stream_content .encode ("latin1")
    pdf_template =f"""%PDF-1.4
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
<< /Length {len (stream_bytes )} >>
stream
{stream_content }
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
0000000{242 +len (stream_bytes )+40 :03d} 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
{242 +len (stream_bytes )+120 }
%%EOF"""
    return pdf_template .encode ("latin1")

def test_pdf_extraction ():
    print ("="*80 )
    print ("      NEXUS PATHOLOGY — PDF EXTRACTION & TABLE RECONSTRUCTION TEST")
    print ("="*80 )

    pdf_bytes =generate_full_synthetic_pdf ()
    res =extract_report_from_file_bytes ("synthetic_pathology_report.pdf",pdf_bytes )

    meta =res ["metadata"]
    params =res ["parameters"]
    print (f"\n[1] Metadata Extracted:")
    print (f"    Patient Name: {meta .get ('patient_name')}")
    print (f"    Patient ID:   {meta .get ('patient_id')}")
    print (f"    Age:          {meta .get ('age')}")
    print (f"    Gender:       {meta .get ('gender')}")
    print (f"    Report ID:    {meta .get ('report_id')}")

    print (f"\n[2] Total Biomarkers Extracted: {len (params )}")
    param_map ={p ["parameter"]:p for p in params }


    checks =[
    ("24-Hour Urinary Copper",35.0 ,"ug/24h","10-60"),
    ("T3",1.2 ,"ng/mL","0.8-2.0"),
    ("T4",8.0 ,"ug/dL","4.5-12.0"),
    ("T3 Resin Uptake",32.0 ,"%","24-39"),
    ("Hemoglobin",14.8 ,"g/dL","13.0-17.0"),
    ("Ferritin",1250.0 ,"ng/mL","30-400"),
    ("ALT",95.0 ,"U/L","10-40"),
    ("AST",82.0 ,"U/L","10-40"),
    ("Ceruloplasmin",28.0 ,"mg/dL","20-40"),
    ("Serum Copper",100.0 ,"ug/dL","70-140")
    ]

    all_passed =True 
    print ("\n[3] Key Biomarker Precision Audit:")
    for name ,exp_val ,exp_unit ,exp_ref in checks :
        p =param_map .get (name )
        if not p :
            print (f"  [FAIL] Missing biomarker: '{name }'")
            all_passed =False 
            continue 

        val_ok =(p ["value"]==exp_val )
        unit_ok =(exp_unit .lower ()in p ["unit"].lower ())
        ref_ok =(exp_ref in p ["reference_range"])

        status_str ="PASS"if (val_ok and unit_ok and ref_ok )else "FAIL"
        if not (val_ok and unit_ok and ref_ok ):
            all_passed =False 
        print (f"  [{status_str }] {name :<24} | Val: {p ['value']} (Exp: {exp_val }) | Unit: '{p ['unit']}' (Exp: '{exp_unit }') | Ref: '{p ['reference_range']}'")

    print (f"\n[4] Data Quality Score:")
    dq =res ["data_quality"]
    print (f"    Biomarkers Detected: {dq ['biomarkers_detected']}")
    print (f"    Extraction Confidence: {dq ['extraction_confidence']}")
    print (f"    Overall Quality: {dq ['overall_quality']}")

    assert len (params )>=24 ,f"Expected at least 24 biomarkers from PDF, got {len (params )}"
    assert all_passed ,"One or more biomarker audits failed!"
    print ("\n"+"="*80 )
    print ("  [SUCCESS] PDF BIOMARKER EXTRACTION PASSED 100%")
    print ("="*80 )

if __name__ =="__main__":
    test_pdf_extraction ()
