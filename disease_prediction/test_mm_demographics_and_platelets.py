"""
Verification for Combined Demographic Header Parsing (58 Yrs / Male) and Platelet Count (210,000).
"""

import unittest 
import urllib .request 
import json 
import uuid 
import sys 
import os 

sys .path .insert (0 ,os .path .abspath (os .path .join (os .path .dirname (__file__ ),"..")))
from disease_prediction .api .report_extractor import (
extract_metadata_and_biomarkers ,
extract_parameters_from_text ,
extract_metadata_from_lines ,
calculate_report_data_quality 
)
from disease_prediction .api .analyzer_service import perform_comprehensive_analysis 
from disease_prediction .api import rare_disease_engine 


SAMPLE_MM_TXT ="""
======================================================================
NEXUS PATHOLOGY DIAGNOSTIC CENTER
PATIENT COMPREHENSIVE LABORATORY REPORT
======================================================================
Patient ID: MM-TEST-098
Patient Name: Arthur Pendelton
Age / Gender: 58 Yrs / Male
Report ID: REP-2026-MM
Report Date: 27-Aug-2026
Referring Doctor: Dr. H. Watson

INVESTIGATION                  OBSERVED VALUE   UNIT        REFERENCE INTERVAL   STATUS
--------------------------------------------------------------------------------------
Total Protein                  10.8             g/dL        6.0 - 8.3            HIGH
Serum Albumin                  2.8              g/dL        3.5 - 5.0            LOW
Serum Globulin                 8.0              g/dL        2.0 - 3.5            HIGH
A/G Ratio                      0.35             ratio       1.0 - 2.2            LOW
Serum Calcium                  12.4             mg/dL       8.5 - 10.5           HIGH
Serum Creatinine               2.4              mg/dL       0.7 - 1.3            HIGH
Hemoglobin                     8.6              g/dL        13.0 - 17.0          LOW
Total Leukocyte Count (WBC)    4800             /uL         4000 - 11000         NORMAL
Platelet Count                 210,000          /uL         150000 - 450000      NORMAL
Monoclonal M Spike             3.8              g/dL        0.0                  HIGH
Immunoglobulin G (IgG)         4200             mg/dL       700 - 1600           HIGH
ESR                            115              mm/1st hr   0 - 15               HIGH
======================================================================
"""


class TestMMDemographicsAndPlatelets (unittest .TestCase ):

    def test_01_demographic_extraction_58_male (self ):
        """Test extraction of 58 Yrs / Male and Patient ID / Name from report."""
        meta ,params =extract_metadata_and_biomarkers (SAMPLE_MM_TXT )
        self .assertEqual (meta .get ("patient_id"),"MM-TEST-098")
        self .assertEqual (meta .get ("patient_name"),"Arthur Pendelton")
        self .assertEqual (meta .get ("age"),58 ,f"Expected 58, got {meta .get ('age')}")
        self .assertEqual (meta .get ("gender"),"Male",f"Expected Male, got {meta .get ('gender')}")
        self .assertEqual (meta .get ("report_id"),"REP-2026-MM")

    def test_02_platelet_count_210000 (self ):
        """Test Platelet Count 210,000 is parsed as 210000.0 without digit loss."""
        meta ,params =extract_metadata_and_biomarkers (SAMPLE_MM_TXT )
        param_map ={p ["canonical_key"]:p for p in params }
        self .assertIn ("PLT",param_map )
        plt =param_map ["PLT"]
        self .assertEqual (plt ["value"],210000.0 ,f"Expected 210000.0, got {plt ['value']}")

    def test_03_multiple_myeloma_pattern (self ):
        """Test Multiple Myeloma pattern is flagged with CRAB features and correct strength."""
        meta ,params =extract_metadata_and_biomarkers (SAMPLE_MM_TXT )
        res =perform_comprehensive_analysis (params ,patient_meta =meta ,metadata =meta )
        ai_res =res ["ai_analysis"]
        rare =ai_res .get ("rare_unusual_screening")or ai_res .get ("rare_disease_screening")
        self .assertTrue (rare ["flagged"])
        self .assertIn ("Myeloma",rare ["condition_name"])
        self .assertIn (rare ["screening_strength"],["HIGH","MODERATE"])

    def test_04_combined_demographic_header_variants (self ):
        """Test all standard clinical report demographic combinations."""
        variants =[
        ("Age / Gender: 58 Yrs / Male",58 ,"Male"),
        ("Age / Sex: 58 / M",58 ,"Male"),
        ("Age/Gender: 58 Yrs / Male",58 ,"Male"),
        ("Age/Sex: 58/M",58 ,"Male"),
        ("Demographics: 58 Yrs / Male",58 ,"Male"),
        ("Demographics: 58 / M",58 ,"Male"),
        ("Age: 58 Yrs / Male",58 ,"Male"),
        ("Age: 58 / Male",58 ,"Male"),
        ("Age: 58 Years, Gender: Male",58 ,"Male"),
        ("58 Yrs / Male",58 ,"Male"),
        ("58 Y / Male",58 ,"Male"),
        ("58/M",58 ,"Male"),
        ("58 Yrs / Female",58 ,"Female"),
        ("58/F",58 ,"Female"),
        ("Male / 58 Yrs",58 ,"Male"),
        ("Female / 62 Yrs",62 ,"Female")
        ]
        for line ,exp_age ,exp_gender in variants :
            meta =extract_metadata_from_lines ([line ])
            self .assertEqual (meta .get ("age"),exp_age ,f"Age mismatch for: '{line }'")
            self .assertEqual (meta .get ("gender"),exp_gender ,f"Gender mismatch for: '{line }'")


def test_live_http_mm ():
    print ("="*80 )
    print ("LIVE MULTIPLE MYELOMA TXT INGESTION & DEMOGRAPHICS TEST")
    print ("="*80 )
    base_url ="http://127.0.0.1:8000"


    req_auth =urllib .request .Request (
    f"{base_url }/api/auth/login",
    data =json .dumps ({"username":"admin","password":"admin123"}).encode ("utf-8"),
    headers ={"Content-Type":"application/json"}
    )
    with urllib .request .urlopen (req_auth ,timeout =10 )as resp :
        token =json .loads (resp .read ().decode ("utf-8"))["token"]


    txt_bytes =SAMPLE_MM_TXT .encode ("utf-8")
    boundary ="----WebKitFormBoundary"+uuid .uuid4 ().hex [:16 ]
    body =(
    f"--{boundary }\r\n"
    f'Content-Disposition: form-data; name="file"; filename="Multiple_Myeloma_Test.txt"\r\n'
    f"Content-Type: text/plain\r\n\r\n"
    ).encode ("utf-8")+txt_bytes +f"\r\n--{boundary }--\r\n".encode ("utf-8")

    req_extract =urllib .request .Request (
    f"{base_url }/api/analyzer/extract",
    data =body ,
    headers ={"Content-Type":f"multipart/form-data; boundary={boundary }"},
    method ="POST"
    )
    with urllib .request .urlopen (req_extract ,timeout =15 )as resp :
        extracted =json .loads (resp .read ().decode ("utf-8"))

    meta =extracted ["metadata"]
    params =extracted ["parameters"]
    param_map ={p ["canonical_key"]:p for p in params }

    print ("\n1. Extracted Metadata:")
    print (f"  Patient ID:   {meta .get ('patient_id')}")
    print (f"  Patient Name: {meta .get ('patient_name')}")
    print (f"  Age:          {meta .get ('age')}")
    print (f"  Gender:       {meta .get ('gender')}")

    assert meta .get ("age")==58 ,f"Expected 58, got {meta .get ('age')}"
    assert meta .get ("gender")=="Male",f"Expected Male, got {meta .get ('gender')}"

    print ("\n2. Platelet Value Check:")
    plt =param_map ["PLT"]
    print (f"  PLT: {plt ['value']} {plt ['unit']}")
    assert plt ["value"]==210000.0 ,f"Expected 210000.0, got {plt ['value']}"


    analyze_payload ={
    "parameters":params ,
    "metadata":meta ,
    "patient_meta":meta ,
    "filename":"Multiple_Myeloma_Test.txt",
    "file_type":"TXT"
    }
    req_analyze =urllib .request .Request (
    f"{base_url }/api/analyzer/analyze",
    data =json .dumps (analyze_payload ).encode ("utf-8"),
    headers ={"Content-Type":"application/json","Authorization":f"Bearer {token }"},
    method ="POST"
    )
    with urllib .request .urlopen (req_analyze ,timeout =40 )as resp :
        anl_res =json .loads (resp .read ().decode ("utf-8"))

    rare =anl_res ["ai_analysis"].get ("rare_unusual_screening")or anl_res ["ai_analysis"].get ("rare_disease_screening")
    print ("\n3. Screening Result:")
    print (f"  Flagged:       {rare ['flagged']}")
    print (f"  Condition:     {rare ['condition_name']}")
    print (f"  Signal:        {rare ['screening_strength']}")

    assert rare ["flagged"]is True 
    assert "Myeloma"in rare ["condition_name"]

    print ("\n[SUCCESS] Live Multiple Myeloma TXT Test Passed 100%!")


if __name__ =="__main__":
    unittest .main (verbosity =2 ,exit =False )
    test_live_http_mm ()
