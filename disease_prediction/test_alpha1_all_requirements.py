"""
Nexus Pathology — Full Verification of Alpha-1 Antitrypsin Rare Disease Detection & Logic Guardrails
Tests:
TEST A: Alpha-1 Antitrypsin PDF (AAT = 42 mg/dL LOW -> AATD HIGH)
TEST B: Wilson Disease PDF (Wilson Disease complete markers -> HIGH)
TEST C: Normal Healthy Adult Control (All normal -> NO HIGH signal)
TEST D: Missing AAT with Liver Abnormalities (ALT/AST HIGH, AAT absent -> AATD NOT HIGH / Insufficient evidence)
"""

import sys 
import os 
import json 
import uuid 
import urllib .request 

sys .path .insert (0 ,os .path .abspath (os .path .join (os .path .dirname (__file__ ),"..")))
from disease_prediction .api .report_extractor import extract_parameters_from_text ,extract_parameters_from_raw_items 
from disease_prediction .api import rare_disease_engine 
from disease_prediction .api import analyzer_service 

BASE_URL ="http://127.0.0.1:8000"

def make_json_req (path ,method ="GET",data =None ,token =None ):
    headers ={"Content-Type":"application/json"}
    if token :
        headers ["Authorization"]=f"Bearer {token }"
    body =json .dumps (data ).encode ("utf-8")if data else None 
    req =urllib .request .Request (f"{BASE_URL }{path }",data =body ,headers =headers ,method =method )
    with urllib .request .urlopen (req ,timeout =30 )as resp :
        return resp .status ,json .loads (resp .read ().decode ("utf-8"))

def test_a_alpha1_pdf ():
    print ("\n"+"="*80 )
    print ("TEST A — ALPHA-1 ANTITRYPSIN PDF EXTRACTION & AATD PATTERN DETECTION")
    print ("="*80 )


    raw_pdf_text ="""
    PATIENT REPORT - NEXUS PATHOLOGY
    Patient Name: Eleanor Vance
    Patient ID: PAT-AAT-882
    Age: 44 Yrs    Gender: Female
    Report ID: REP-2026-AAT-01

    ========================================================================================
    PARAMETER                      OBSERVED VALUE   UNIT         REFERENCE RANGE   STATUS
    ========================================================================================
    Alpha-1 Antitrypsin            42.0             mg/dL        90.0 - 200.0      LOW
    ALT                            118.0            U/L          10 - 40           HIGH
    AST                            96.0             U/L          10 - 40           HIGH
    Total Bilirubin                1.8              mg/dL        0.2 - 1.2         HIGH
    Albumin                        3.2              g/dL         3.5 - 5.0         LOW
    Total Protein                  6.8              g/dL         6.0 - 8.3         NORMAL
    Ceruloplasmin                  27.0             mg/dL        20 - 40           NORMAL
    Serum Copper                   102.0            ug/dL        70 - 140          NORMAL
    24-Hour Urinary Copper         32.0             ug/24h       10 - 60           NORMAL
    Ferritin                       180.0            ng/mL        30 - 400          NORMAL
    Serum Iron                     105.0            ug/dL        60 - 170          NORMAL
    Transferrin Saturation         31.0             %            20 - 50           NORMAL
    Hemoglobin                     13.5             g/dL         12.0 - 15.0       NORMAL
    WBC Count                      6200             /uL          4000 - 11000      NORMAL
    Platelet Count                 225000           /uL          150000 - 450000   NORMAL
    ========================================================================================
    """

    raw_items =extract_parameters_from_text (raw_pdf_text )
    params =extract_parameters_from_raw_items (raw_items )

    param_map ={p ["canonical_key"]:p for p in params }
    print (f"Extracted {len (params )} biomarkers from report.")

    assert "ALPHA1_ANTITRYPSIN"in param_map ,"ALPHA1_ANTITRYPSIN missing from extracted biomarkers!"
    aat =param_map ["ALPHA1_ANTITRYPSIN"]
    print (f"  [RAW PDF TEXT FOUND] : 'Alpha-1 Antitrypsin            42.0             mg/dL        90.0 - 200.0      LOW'")
    print (f"  [NORMALIZED NAME]    : {aat ['normalized_name']} (Canonical Key: {aat ['canonical_key']})")
    print (f"  [EXTRACTED VALUE]    : {aat ['value']}")
    print (f"  [EXTRACTED UNIT]     : {aat ['unit']}")
    print (f"  [EXTRACTED REF RANGE]: {aat ['reference_range']}")
    print (f"  [STATUS]             : {aat ['status']}")

    assert aat ["value"]==42.0 
    assert aat ["unit"]=="mg/dL"
    assert aat ["status"]=="LOW"


    res =rare_disease_engine .evaluate_rare_disease_patterns (params ,{"age":44 ,"gender":"Female"})
    print (f"\nRare Disease Engine Evaluation:")
    print (f"  Flagged:             {res ['flagged']}")
    print (f"  Top Condition Name:  {res ['condition_name']}")
    print (f"  Screening Strength:  {res ['screening_strength']}")

    assert res ["flagged"]is True 
    assert "Alpha-1 Antitrypsin"in res ["condition_name"]
    assert res ["screening_strength"]=="HIGH"


    top_cond =res ["conditions"][0 ]
    print (f"  Candidate Card:      {top_cond ['short_name']} (Concordance: {top_cond ['concordance_pct']}%)")
    print (f"  Primary Ratio:       {top_cond ['primary_ratio']}")
    print (f"  Supporting Ratio:    {top_cond ['supporting_ratio']}")
    assert top_cond ["primary_matches_count"]>=1 
    assert top_cond ["concordance_pct"]>=76 

    print ("TEST A: PASS [100%]")


def test_b_wilson_disease_pdf ():
    print ("\n"+"="*80 )
    print ("TEST B — WILSON DISEASE COMPLETE CONCORDANT BIOMARKERS")
    print ("="*80 )

    raw_wilson_text ="""
    Patient Name: Alex Rivera
    Age: 24 Yrs    Gender: Male
    Ceruloplasmin: 8.5 mg/dL (20-40) LOW
    24-Hour Urinary Copper: 145 ug/24h (10-60) HIGH
    Serum Copper: 45 ug/dL (70-140) LOW
    ALT: 95 U/L (10-40) HIGH
    AST: 82 U/L (10-40) HIGH
    Total Bilirubin: 2.8 mg/dL (0.2-1.2) HIGH
    Indirect Bilirubin: 1.9 mg/dL (0.1-0.8) HIGH
    LDH: 380 U/L (140-280) HIGH
    Haptoglobin: 12 mg/dL (30-200) LOW
    Hemoglobin: 10.2 g/dL (13-17) LOW
    """
    raw_items =extract_parameters_from_text (raw_wilson_text )
    params =extract_parameters_from_raw_items (raw_items )

    res =rare_disease_engine .evaluate_rare_disease_patterns (params ,{"age":24 ,"gender":"Male"})
    print (f"Wilson Disease Evaluation:")
    print (f"  Flagged:             {res ['flagged']}")
    print (f"  Top Condition Name:  {res ['condition_name']}")
    print (f"  Screening Strength:  {res ['screening_strength']}")

    assert res ["flagged"]is True 
    assert "Wilson"in res ["condition_name"]
    assert res ["screening_strength"]=="HIGH"
    top_cond =res ["conditions"][0 ]
    assert top_cond ["primary_matches_count"]>=2 
    print (f"  Primary Ratio:       {top_cond ['primary_ratio']}")
    print (f"  Concordance:         {top_cond ['concordance_pct']}%")

    print ("TEST B: PASS [100%]")


def test_c_normal_control ():
    print ("\n"+"="*80 )
    print ("TEST C — NORMAL HEALTHY ADULT CONTROL")
    print ("="*80 )

    raw_normal_text ="""
    Hemoglobin: 14.8 g/dL (13.0-17.0) NORMAL
    Total Bilirubin: 0.8 mg/dL (0.2-1.2) NORMAL
    ALT: 22 U/L (10-40) NORMAL
    AST: 24 U/L (10-40) NORMAL
    Ceruloplasmin: 28.0 mg/dL (20-40) NORMAL
    Serum Copper: 98.0 ug/dL (70-140) NORMAL
    24-Hour Urinary Copper: 25.0 ug/24h (10-60) NORMAL
    Alpha-1 Antitrypsin: 145.0 mg/dL (90-200) NORMAL
    Ferritin: 120 ng/mL (30-400) NORMAL
    TSH: 2.1 uIU/mL (0.4-4.2) NORMAL
    """
    raw_items =extract_parameters_from_text (raw_normal_text )
    params =extract_parameters_from_raw_items (raw_items )

    res =rare_disease_engine .evaluate_rare_disease_patterns (params ,{"age":30 ,"gender":"Female"})
    print (f"Normal Control Evaluation:")
    print (f"  Flagged:             {res ['flagged']}")
    print (f"  Top Condition Name:  {res ['condition_name']}")
    print (f"  Screening Strength:  {res ['screening_strength']}")

    assert res ["flagged"]is False 
    assert res ["screening_strength"]=="NONE"
    assert len (res ["conditions"])==0 
    print ("  Unsupported Conditions Count:",len (res ["unsupported_conditions"]))

    print ("TEST C: PASS [100%]")


def test_d_missing_aat_with_isolated_liver_abnormalities ():
    print ("\n"+"="*80 )
    print ("TEST D — LIVER ABNORMALITIES WITH MISSING AAT RESULT")
    print ("="*80 )


    raw_liver_text ="""
    Patient Name: Robert Chen
    Age: 52 Yrs    Gender: Male
    ALT: 118 U/L (10-40) HIGH
    AST: 96 U/L (10-40) HIGH
    Total Bilirubin: 1.8 mg/dL (0.2-1.2) HIGH
    Albumin: 3.4 g/dL (3.5-5.0) LOW
    Total Protein: 7.0 g/dL (6.0-8.3) NORMAL
    Ceruloplasmin: 27.0 mg/dL (20-40) NORMAL
    Serum Copper: 102.0 ug/dL (70-140) NORMAL
    24-Hour Urinary Copper: 32.0 ug/24h (10-60) NORMAL
    Ferritin: 180.0 ng/mL (30-400) NORMAL
    """
    raw_items =extract_parameters_from_text (raw_liver_text )
    params =extract_parameters_from_raw_items (raw_items )

    res =rare_disease_engine .evaluate_rare_disease_patterns (params ,{"age":52 ,"gender":"Male"})
    print (f"Evaluation with missing AAT:")
    print (f"  Flagged:             {res ['flagged']}")
    print (f"  Top Condition Name:  {res ['condition_name']}")
    print (f"  Screening Strength:  {res ['screening_strength']}")


    for cond in res ["conditions"]:
        if "Alpha-1"in cond ["name"]:
            assert cond ["screening_strength"]!="HIGH","AATD must NEVER receive HIGH without AAT primary evidence!"
            assert cond ["primary_matches_count"]==0 

    assert "Alpha-1"not in res ["condition_name"],"AATD must not be top condition when AAT is missing!"
    print (f"  [PASS] AATD correctly rejected from HIGH screening due to missing disease-specific primary marker.")

    print ("TEST D: PASS [100%]")


if __name__ =="__main__":
    test_a_alpha1_pdf ()
    test_b_wilson_disease_pdf ()
    test_c_normal_control ()
    test_d_missing_aat_with_isolated_liver_abnormalities ()
    print ("\n"+"="*80 )
    print ("  ALL 4 CLINICAL DECISION-SUPPORT TESTS PASSED 100%")
    print ("="*80 )
