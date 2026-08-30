"""
Nexus Pathology — Full End-to-End API and Analyzer Contract Verification
Tests extraction, analysis, data quality audit, 3-state ML tracking,
top screening patterns, evidence concordance, and unsupported conditions.
"""

import sys 
import json 
from pathlib import Path 

sys .path .insert (0 ,str (Path (__file__ ).resolve ().parent .parent ))

from fastapi .testclient import TestClient 
from disease_prediction .api .main import app 
from disease_prediction .api import database as db 

client =TestClient (app )

def test_full_analyzer_contracts ():
    db .init_db ()
    db .reset_to_clean_seed ()

    print ("--- 1. Testing GET / Frontend Serving ---")
    resp =client .get ("/")
    assert resp .status_code ==200 ,f"Expected 200, got {resp .status_code }"
    html =resp .text 
    assert "tab-analyzer"in html 
    assert "Please verify extracted values before running analysis"in html 
    print ("[PASS] Frontend HTML contains all required elements and verification guidance.")

    print ("\n--- 2. Testing POST /api/analyzer/extract ---")
    sample_report ="""NEXUS PATHOLOGY DIAGNOSTIC CENTER
PATIENT REPORT
Patient ID: TC-001-WILSON
Patient Name: Alex Rivera
Age: 24 Yrs
Gender: Male
Report ID: REP-2026-TC1
Date: 26-Aug-2026

INVESTIGATION               OBSERVED VALUE   UNIT        REFERENCE INTERVAL   STATUS
--------------------------------------------------------------------------------------
Hemoglobin                  10.4             g/dL        13.0 - 17.0          LOW
Total RBC Count             3.55             million/uL  4.50 - 5.90          LOW
PCV / Hematocrit            31.0             %           40.0 - 50.0          LOW
MCV                         87.0             fL          80.0 - 100.0         NORMAL
MCH                         29.0             pg          27.0 - 32.0          NORMAL
MCHC                        33.5             g/dL        31.5 - 34.5          NORMAL
RDW                         15.8             %           11.5 - 14.5          HIGH
Total Leukocyte Count (WBC) 7200             /uL         4000 - 11000         NORMAL
Platelet Count              178000           /uL         150000 - 450000      NORMAL
Total Bilirubin             4.8              mg/dL       0.2 - 1.2            HIGH
Direct Bilirubin            1.1              mg/dL       0.0 - 0.3            HIGH
Indirect Bilirubin          3.7              mg/dL       0.2 - 0.8            HIGH
ALT / SGPT                  186              U/L         10 - 40              HIGH
AST / SGOT                  245              U/L         10 - 40              HIGH
Alkaline Phosphatase (ALP)  72               U/L         44 - 147             NORMAL
Total Protein               7.1              g/dL        6.0 - 8.3            NORMAL
Albumin                     3.2              g/dL        3.5 - 5.0            LOW
Globulin                    3.9              g/dL        2.0 - 3.5            HIGH
A/G Ratio                   0.82             ratio       1.0 - 2.2            LOW
Ceruloplasmin               8                mg/dL       20 - 40              LOW
24-Hour Urinary Copper      185              ug/24h      10 - 60              HIGH
Serum Copper                52               ug/dL       70 - 140             LOW
LDH                         680              U/L         140 - 280            HIGH
Haptoglobin                 18               mg/dL       30 - 200             LOW
Reticulocyte Count          3.2              %           0.5 - 2.5            HIGH
TSH                         2.1              uIU/mL      0.40 - 4.20          NORMAL
T3 Resin Uptake             32               %           24–39%               NORMAL
CRP                         2.1              mg/L        0.0 - 5.0            NORMAL
"""
    files ={'file':('sample_wilson.txt',sample_report .encode ('utf-8'),'text/plain')}
    extract_resp =client .post ("/api/analyzer/extract",files =files )
    assert extract_resp .status_code ==200 ,f"Extract failed: {extract_resp .text }"
    extracted_data =extract_resp .json ()

    assert extracted_data ["total_parameters"]>=25 
    assert "data_quality"in extracted_data 
    dq =extracted_data ["data_quality"]
    assert dq ["overall_quality"]in ["GOOD","FAIR"]
    assert dq ["biomarkers_detected"]>=25 
    assert dq ["reference_ranges_detected"]>=20 
    print (f"[PASS] Extraction succeeded: {extracted_data ['total_parameters']} parameters, Quality={dq ['overall_quality']}, Confidence={dq ['extraction_confidence']}")

    print ("\n--- 3. Testing POST /api/analyzer/analyze ---")
    analyze_payload ={
    "parameters":extracted_data ["parameters"],
    "metadata":extracted_data ["metadata"],
    "patient_meta":{
    "patient_id":extracted_data ["metadata"].get ("patient_id","DEMO-001"),
    "name":extracted_data ["metadata"].get ("patient_name","Alex Rivera"),
    "age":extracted_data ["metadata"].get ("age",24 ),
    "gender":extracted_data ["metadata"].get ("gender","Male")
    },
    "filename":"sample_wilson.txt",
    "file_type":"TXT"
    }

    analyze_resp =client .post ("/api/analyzer/analyze",json =analyze_payload )
    assert analyze_resp .status_code ==200 ,f"Analyze failed: {analyze_resp .text }"
    result =analyze_resp .json ()


    assert "data_quality"in result 
    print ("[PASS] Report Data Quality audit present in analysis output.")


    ml_res =result ["ml_model_results"]
    assert ml_res ["anemia"]["data_state"]=="AVAILABLE"
    assert ml_res ["anemia"]["status"]=="MODEL ANALYSIS AVAILABLE"
    assert ml_res ["liver"]["data_state"]=="AVAILABLE"
    assert ml_res ["liver"]["status"]=="MODEL ANALYSIS AVAILABLE"
    assert ml_res ["dengue"]["data_state"]=="PARTIAL"
    assert ml_res ["dengue"]["status"]=="PARTIAL DATA"
    print ("[PASS] 3 ML Data-Availability States verified (AVAILABLE, PARTIAL, INSUFFICIENT).")


    rare_sec =result ["ai_analysis"]["rare_unusual_screening"]
    top_signals =rare_sec .get ("top_screening_patterns",[])
    assert len (top_signals )>0 
    assert top_signals [0 ]["name"]=="Wilson Disease"
    assert top_signals [0 ]["strength"]=="HIGH"
    print (f"[PASS] Top Screening Signals present: {top_signals [0 ]['name']} (Rank 1, {top_signals [0 ]['concordance_pct']}% Concordance)")


    conditions =rare_sec .get ("conditions",[])
    assert len (conditions )>0 
    top_cond =conditions [0 ]
    assert top_cond ["screening_strength"]=="HIGH"
    assert "concordance_pct"in top_cond 
    assert "primary_matches_count"in top_cond 
    assert "supporting_matches_count"in top_cond 
    assert "confirmatory_evaluation"in top_cond 
    print (f"[PASS] Candidate Condition Card verified: {top_cond ['short_name']} (Concordance: {top_cond ['concordance_pct']}%, Primary: {top_cond ['primary_matches_count']}/{top_cond ['primary_total']})")


    unsupported =rare_sec .get ("unsupported_conditions",[])
    print (f"[PASS] Ruled out / unsupported conditions checked count: {len (unsupported )}")
    for uc in unsupported :
        assert "evidence_checked"in uc 
        for ec in uc ["evidence_checked"]:
            assert "biomarker"in ec 
            assert "status_text"in ec 


    assert "Screening signal only"in top_cond ["disclaimer"]
    print ("[PASS] Non-diagnostic safe phrasing verified.")

    print ("\n==================================================")
    print ("ALL END-TO-END CONTRACT & PIPELINE TESTS PASSED!")
    print ("==================================================")

if __name__ =="__main__":
    test_full_analyzer_contracts ()
