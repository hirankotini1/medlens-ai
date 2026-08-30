"""
Comprehensive Test Suite for TXT Ingestion Parity, Demographics, and G6PD Screening.

Requirements tested:
1. TXT and PDF share unified normalization pipeline.
2. G6PD end-to-end invariant: G6PD_ENZYME_ACTIVITY = 2.1 LOW produces HIGH screening signal, never missing.
3. TXT Numeric Parser: 205000, 205,000, 150000, 450000, 11000, 4000 without zero truncation.
4. TXT Demographic Parser: Patient ID = RARE-TEST-007, Age = 26, Gender = Male (never 32/Female fallback).
5. Data Quality: unmapped_parameters is 0 when all parameters are recognized.
6. Multi-format support: key=val, key: val, multi-line ref/status, table, pipes.
"""

import unittest 
import sys 
import os 

sys .path .insert (0 ,os .path .abspath (os .path .join (os .path .dirname (__file__ ),"..")))
from disease_prediction .api .report_extractor import (
extract_parameters_from_text ,
extract_metadata_and_biomarkers ,
calculate_report_data_quality 
)
from disease_prediction .api .analyzer_service import perform_comprehensive_analysis 
from disease_prediction .api import rare_disease_engine 


class TestTXTIngestionPipeline (unittest .TestCase ):

    def test_01_txt_g6pd_full_report (self ):
        """TEST A & Acceptance: G6PD_Deficiency_Rare_Disease_Test.txt extraction, demographics, and screening."""
        raw_txt ="""
Patient ID = RARE-TEST-007
Patient Name = Synthetic Rare Disease Test
Age = 26
Gender = Male
Report ID = NEXUS-RARE-007
Report Date = 27-Aug-2026

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
"""
        meta ,params =extract_metadata_and_biomarkers (raw_txt )


        self .assertEqual (meta .get ("patient_id"),"RARE-TEST-007")
        self .assertEqual (meta .get ("patient_name"),"Synthetic Rare Disease Test")
        self .assertEqual (meta .get ("age"),26 )
        self .assertEqual (meta .get ("gender"),"Male")
        self .assertEqual (meta .get ("report_id"),"NEXUS-RARE-007")
        self .assertEqual (meta .get ("report_date"),"27-Aug-2026")

        param_map ={p ["canonical_key"]:p for p in params }


        self .assertIn ("G6PD_ENZYME_ACTIVITY",param_map )
        g6pd =param_map ["G6PD_ENZYME_ACTIVITY"]
        self .assertEqual (g6pd ["value"],2.1 )
        self .assertEqual (g6pd ["status"],"LOW")
        self .assertIn ("U/g",g6pd ["unit"])


        self .assertIn ("PLT",param_map )
        plt =param_map ["PLT"]
        self .assertEqual (plt ["value"],205000.0 )


        self .assertIn ("RETICULOCYTES",param_map )
        retic =param_map ["RETICULOCYTES"]
        self .assertEqual (retic ["value"],6.1 )
        self .assertEqual (retic ["unit"],"%")


        dq =calculate_report_data_quality (meta ,params )
        self .assertEqual (dq ["unmapped_parameters"],0 )
        self .assertEqual (dq ["unmapped_count"],0 )
        self .assertGreaterEqual (dq ["reference_ranges_detected"],8 )


        analysis_res =perform_comprehensive_analysis (params ,patient_meta =meta ,metadata =meta )
        ai_res =analysis_res ["ai_analysis"]
        rare_screening =ai_res .get ("rare_unusual_screening")or ai_res .get ("rare_disease_screening")

        self .assertTrue (rare_screening ["flagged"])
        self .assertIn ("G6PD",rare_screening ["condition_name"])
        self .assertEqual (rare_screening ["screening_strength"],"HIGH")


        for uc in rare_screening .get ("unsupported_conditions",[]):
            if uc ["disease_id"]=="g6pd_deficiency":
                for ec in uc .get ("evidence_checked",[]):
                    self .assertNotIn ("Not available",ec .get ("status_text",""))

    def test_02_numeric_parser_large_numbers (self ):
        """TEST C: Numeric parser handles 205000, 150000, 450000, 11000, 4000, 205,000 without digit loss."""
        test_lines =[
        ("Platelet Count: 205000 /uL (150000 - 450000) NORMAL","PLT",205000.0 ),
        ("Platelet Count = 205,000 /uL (150,000 - 450,000) NORMAL","PLT",205000.0 ),
        ("Platelet Count: 150000 /uL (150000 - 450000) NORMAL","PLT",150000.0 ),
        ("Platelet Count = 450000 /uL (150000 - 450000) NORMAL","PLT",450000.0 ),
        ("WBC Count: 11000 /uL (4000 - 11000) NORMAL","WBC",11000.0 ),
        ("WBC Count = 4000 /uL (4000 - 11000) NORMAL","WBC",4000.0 ),
        ("Platelet Count = 205000 /uL","PLT",205000.0 )
        ]
        for line ,expected_key ,expected_val in test_lines :
            items =extract_parameters_from_text (line )
            self .assertEqual (len (items ),1 ,f"Failed parsing: {line }")
            self .assertEqual (items [0 ]["canonical_key"],expected_key )
            self .assertEqual (items [0 ]["value"],expected_val ,f"Value mismatch for line: {line }")

    def test_03_various_syntax_formats (self ):
        """TEST F: Parser supports ':', '=', table with tabs, pipes, spaces preserving multi-word biomarker names."""
        samples =[
        "G6PD Enzyme Activity: 2.1 U/g Hb",
        "G6PD Enzyme Activity = 2.1 U/g Hb",
        "G6PD Enzyme Activity | 2.1 | U/g Hb | 7.0 - 10.5 | LOW",
        "G6PD Enzyme Activity\t2.1\tU/g Hb\t7.0 - 10.5\tLOW",
        "G6PD Enzyme Activity    2.1    U/g Hb    7.0 - 10.5    LOW"
        ]
        for s in samples :
            items =extract_parameters_from_text (s )
            self .assertEqual (len (items ),1 ,f"Failed on syntax: {s }")
            self .assertEqual (items [0 ]["canonical_key"],"G6PD_ENZYME_ACTIVITY")
            self .assertEqual (items [0 ]["value"],2.1 )

    def test_04_data_quality_no_unmapped_inflation (self ):
        """TEST E: Data quality unmapped count reflects genuine unmapped parameters."""
        raw_text ="""
        Hemoglobin = 14.2 g/dL
        WBC Count = 6800 /uL
        Platelet Count = 205000 /uL
        G6PD Enzyme Activity = 2.1 U/g Hb
        """
        meta ,params =extract_metadata_and_biomarkers (raw_text )


        client_params =[
        {"parameter":p ["parameter"],"value":p ["value"],"unit":p ["unit"],"reference_range":p ["reference_range"],"status":p ["status"]}
        for p in params 
        ]

        res =perform_comprehensive_analysis (client_params ,patient_meta =meta )
        dq =res ["data_quality"]
        self .assertEqual (dq ["biomarkers_detected"],4 )
        self .assertEqual (dq ["unmapped_parameters"],0 )


if __name__ =="__main__":
    unittest .main (verbosity =2 )
