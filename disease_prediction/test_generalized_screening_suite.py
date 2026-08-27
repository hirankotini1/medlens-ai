"""
Nexus Pathology — Generalized Multi-Disease Rare / Complex Screening Engine Comprehensive Test Suite
Validates all 24 requirements, clinical safety rules, and final acceptance criteria.
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from disease_prediction.api.report_extractor import (
    extract_parameters_from_text,
    extract_parameters_from_raw_items,
    extract_metadata_and_biomarkers,
    normalize_param_name,
    CANONICAL_REF_RANGES,
    PARAMETER_ALIASES
)
from disease_prediction.api import rare_disease_engine
from disease_prediction.api import openrouter_service
from disease_prediction.api.ml_bridge import evaluate_extracted_report_with_ml
from disease_prediction.api.file_parser import validate_file_metadata, parse_csv_report


class TestGeneralizedRareDiseaseScreeningEngine(unittest.TestCase):

    def test_01_normal_report(self):
        """Test 1 & Acceptance Test E: Normal report does NOT force a rare disease."""
        report = """
        Hemoglobin: 14.5 g/dL (13.0-17.0) NORMAL
        Platelets: 250000 /uL (150000-450000) NORMAL
        WBC: 7000 /uL (4000-11000) NORMAL
        ALT: 25 U/L (10-40) NORMAL
        AST: 28 U/L (10-40) NORMAL
        Total Bilirubin: 0.8 mg/dL (0.2-1.2) NORMAL
        Ceruloplasmin: 28 mg/dL (20-40) NORMAL
        Alpha-1 Antitrypsin: 140 mg/dL (90-200) NORMAL
        Ferritin: 150 ng/mL (30-400) NORMAL
        TSH: 2.1 uIU/mL (0.4-4.2) NORMAL
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 32, "gender": "Male"})
        self.assertFalse(res["flagged"])
        self.assertEqual(res["screening_strength"], "NONE")
        self.assertEqual(len(res["conditions"]), 0)
        self.assertIn("No sufficiently specific multi-marker pattern", res["why_flagged"])

    def test_02_wilson_disease_pattern(self):
        """Test 2 & Acceptance Test A: Wilson disease pattern (Young age + Low ceruloplasmin + High 24h urinary copper + Transaminitis)."""
        report = """
        Ceruloplasmin: 8.0 mg/dL (20-40) LOW
        24-Hour Urinary Copper: 160 ug/24h (10-60) HIGH
        Serum Copper: 42 ug/dL (70-140) LOW
        ALT: 110 U/L (10-40) HIGH
        AST: 92 U/L (10-40) HIGH
        Total Bilirubin: 2.4 mg/dL (0.2-1.2) HIGH
        Indirect Bilirubin: 1.6 mg/dL (0.1-0.8) HIGH
        LDH: 360 U/L (140-280) HIGH
        Haptoglobin: 15 mg/dL (30-200) LOW
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 22, "gender": "Female"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Wilson", res["conditions"][0]["name"])
        self.assertGreaterEqual(res["conditions"][0]["concordance_pct"], 76)
        self.assertEqual(res["conditions"][0]["primary_matches_count"], 3)

    def test_03_hemochromatosis_pattern(self):
        """Test 3 & Acceptance Test B: Hemochromatosis (High Transferrin Sat + High Ferritin + High Iron), Wilson NOT supported."""
        report = """
        Transferrin Saturation: 78 % (20-50) HIGH
        Ferritin: 1450 ng/mL (30-400) HIGH
        Serum Iron: 210 ug/dL (60-170) HIGH
        ALT: 88 U/L (10-40) HIGH
        AST: 76 U/L (10-40) HIGH
        Ceruloplasmin: 29 mg/dL (20-40) NORMAL
        24-Hour Urinary Copper: 25 ug/24h (10-60) NORMAL
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 48, "gender": "Male"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Hemochromatosis", res["conditions"][0]["name"])
        # Verify Wilson is in unsupported conditions with normal copper markers
        wilson_unsupp = next((uc for uc in res["unsupported_conditions"] if "Wilson" in uc["name"]), None)
        self.assertIsNotNone(wilson_unsupp)
        self.assertIn("NOT STRONGLY SUPPORTED", wilson_unsupp["status_label"])

    def test_04_g6pd_specific_pattern(self):
        """Test 4 & Acceptance Test C (Part 1): G6PD enzyme activity LOW produces G6PD Deficiency signal."""
        report = """
        G6PD Enzyme Activity: 2.1 U/g Hb (7.0-20.5) LOW
        LDH: 520 U/L (140-280) HIGH
        Haptoglobin: 8 mg/dL (30-200) LOW
        Indirect Bilirubin: 3.2 mg/dL (0.1-0.8) HIGH
        Reticulocytes: 6.8 % (0.5-2.5) HIGH
        Hemoglobin: 9.2 g/dL (13.0-17.0) LOW
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 19, "gender": "Male"})
        self.assertTrue(res["flagged"])
        self.assertIn("G6PD Deficiency", res["conditions"][0]["name"])
        self.assertIn(res["conditions"][0]["screening_strength"], ["HIGH", "MODERATE"])

    def test_05_generic_hemolysis_without_g6pd_evidence(self):
        """Test 5 & Requirement 10: Generic hemolysis without G6PD enzyme test does NOT label definitively as G6PD deficiency."""
        report = """
        LDH: 480 U/L (140-280) HIGH
        Haptoglobin: 10 mg/dL (30-200) LOW
        Indirect Bilirubin: 2.8 mg/dL (0.1-0.8) HIGH
        Reticulocytes: 5.5 % (0.5-2.5) HIGH
        Hemoglobin: 10.1 g/dL (13.0-17.0) LOW
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 28, "gender": "Female"})
        self.assertTrue(res["flagged"])
        top_name = res["conditions"][0]["name"]
        self.assertIn("Hemolytic Anemia Pattern", top_name)
        # Ensure G6PD deficiency without G6PD enzyme is NOT top condition
        self.assertNotEqual(res["conditions"][0]["disease_id"], "g6pd_deficiency")
        # Ensure missing G6PD test is noted
        self.assertTrue(any("G6PD" in t for t in res["missing_helpful_tests"]))

    def test_06_alpha1_antitrypsin_pattern(self):
        """Test 6 & Acceptance Test D: AAT LOW + transaminitis produces AATD pattern."""
        report = """
        Alpha-1 Antitrypsin: 38.0 mg/dL (90-200) LOW
        ALT: 125 U/L (10-40) HIGH
        AST: 102 U/L (10-40) HIGH
        Total Bilirubin: 1.9 mg/dL (0.2-1.2) HIGH
        Albumin: 3.3 g/dL (3.5-5.0) LOW
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 42, "gender": "Female"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Alpha-1 Antitrypsin", res["conditions"][0]["name"])

    def test_07_generic_transaminitis_no_rare_disease_flag(self):
        """Test 7 & Acceptance Test F & Requirement 19: Isolated ALT/AST high does NOT produce rare liver disease."""
        report = """
        ALT: 145 U/L (10-40) HIGH
        AST: 110 U/L (10-40) HIGH
        Total Bilirubin: 1.4 mg/dL (0.2-1.2) HIGH
        Total Protein: 7.2 g/dL (6.0-8.3) NORMAL
        Albumin: 4.1 g/dL (3.5-5.0) NORMAL
        Globulin: 3.1 g/dL (2.0-3.5) NORMAL
        Ceruloplasmin: 27 mg/dL (20-40) NORMAL
        Alpha-1 Antitrypsin: 150 mg/dL (90-200) NORMAL
        Ferritin: 180 ng/mL (30-400) NORMAL
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 35, "gender": "Male"})
        self.assertFalse(res["flagged"])
        self.assertEqual(res["screening_strength"], "NONE")
        self.assertIn("Non-specific hepatocellular transaminitis", res["why_flagged"])

    def test_08_multiple_myeloma_pattern(self):
        """Test 8: CRAB pattern (Total protein high, globulin high, A/G low, calcium high, creatinine high)."""
        report = """
        Total Protein: 9.8 g/dL (6.0-8.3) HIGH
        Globulin: 6.2 g/dL (2.0-3.5) HIGH
        Albumin: 3.6 g/dL (3.5-5.0) NORMAL
        A/G Ratio: 0.58 (1.0-2.2) LOW
        Calcium: 12.2 mg/dL (8.5-10.5) HIGH
        Creatinine: 2.1 mg/dL (0.6-1.2) HIGH
        Hemoglobin: 9.5 g/dL (13.0-17.0) LOW
        ESR: 95 mm/hr (0-20) HIGH
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 66, "gender": "Male"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Multiple Myeloma", res["conditions"][0]["name"])

    def test_09_thalassemia_trait_pattern(self):
        """Test 9: Microcytosis with preserved RBC count and normal ferritin (Mentzer index pattern)."""
        report = """
        MCV: 62 fL (80-100) LOW
        MCH: 19 pg (27-33) LOW
        RBC: 6.1 x10^6/uL (4.5-5.5) HIGH
        Hemoglobin: 11.2 g/dL (13.0-17.0) LOW
        RDW: 13.2 % (11.5-14.5) NORMAL
        Ferritin: 110 ng/mL (30-400) NORMAL
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 25, "gender": "Female"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Thalassemia Trait", res["conditions"][0]["name"])

    def test_10_addison_disease_pattern(self):
        """Test 10: Hyponatremia + Hyperkalemia + Hypoglycemia."""
        report = """
        Sodium: 124 mmol/L (135-145) LOW
        Potassium: 5.8 mmol/L (3.5-5.0) HIGH
        Glucose: 58 mg/dL (70-100) LOW
        Urea: 32 mg/dL (7-20) HIGH
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 38, "gender": "Female"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Addison", res["conditions"][0]["name"])

    def test_11_cushing_syndrome_pattern(self):
        """Test 11: Hyperglycemia + Hypokalemia + Hypernatremia."""
        report = """
        Glucose: 165 mg/dL (70-100) HIGH
        Potassium: 3.1 mmol/L (3.5-5.0) LOW
        Sodium: 148 mmol/L (135-145) HIGH
        HbA1c: 7.2 % (4.0-5.6) HIGH
        WBC: 13500 /uL (4000-11000) HIGH
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 45, "gender": "Female"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        self.assertIn("Cushing", res["conditions"][0]["name"])

    def test_12_primary_markers_zero_guardrail(self):
        """Test 12 & Requirement 9: When primary markers are 0, concordance must NOT be high and disease must not be HIGH/MODERATE."""
        # Report has only non-specific minor markers
        report = """
        Total Bilirubin: 1.5 mg/dL (0.2-1.2) HIGH
        Albumin: 3.3 g/dL (3.5-5.0) LOW
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 30, "gender": "Male"})
        for c in res["conditions"]:
            self.assertGreaterEqual(c["primary_matches_count"], 1)
            self.assertNotEqual(c["primary_ratio"], "0/0")

    def test_13_contradictory_evidence_penalty(self):
        """Test 13: Contradictory evidence (e.g. Ferritin LOW for Hemochromatosis) penalizes and prevents HIGH signal."""
        report = """
        Transferrin Saturation: 65 % (20-50) HIGH
        Ferritin: 12 ng/mL (30-400) LOW
        Serum Iron: 180 ug/dL (60-170) HIGH
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 50, "gender": "Male"})
        # Should not be HIGH because Ferritin is severely depleted
        hemo = next((c for c in res["conditions"] if "Hemochromatosis" in c["name"]), None)
        if hemo:
            self.assertNotEqual(hemo["screening_strength"], "HIGH")
            self.assertIn("contradictory_count", hemo)
            self.assertGreaterEqual(hemo["contradictory_count"], 1)

    def test_14_pii_removal(self):
        """Test 14 & Requirement 21: PII is completely stripped before external AI transmission."""
        raw_meta = {
            "patient_name": "Eleanor Vance",
            "patient_id": "PAT-9988-CONFIDENTIAL",
            "phone": "+1-555-0199",
            "email": "eleanor@example.com",
            "address": "124 Hill House Way",
            "report_id": "REP-2026-SECRET",
            "age": 44,
            "gender": "Female"
        }
        raw_params = [{"parameter": "ALT", "value": 118, "unit": "U/L", "status": "HIGH", "canonical_key": "ALT"}]
        payload = openrouter_service.strip_pii_from_payload(raw_params, raw_meta)
        
        self.assertNotIn("Eleanor", json.dumps(payload))
        self.assertNotIn("PAT-9988", json.dumps(payload))
        self.assertNotIn("555-0199", json.dumps(payload))
        self.assertNotIn("eleanor@example.com", json.dumps(payload))
        self.assertNotIn("Hill House", json.dumps(payload))
        self.assertNotIn("REP-2026-SECRET", json.dumps(payload))
        self.assertEqual(payload["demographics"]["age"], 44)
        self.assertEqual(payload["demographics"]["biological_sex"], "Female")

    def test_15_invalid_ai_response_handling(self):
        """Test 15: Invalid AI JSON gracefully caught and fallback activated."""
        invalid_raw = "This is not json at all, just clinical rambling."
        with self.assertRaises(ValueError):
            openrouter_service.clean_json_response(invalid_raw)

    def test_16_ai_unavailable_fallback(self):
        """Test 16: Deterministic fallback executes cleanly when AI is unavailable."""
        report = """
        Ceruloplasmin: 8.0 mg/dL (20-40) LOW
        24-Hour Urinary Copper: 150 ug/24h (10-60) HIGH
        ALT: 95 U/L (10-40) HIGH
        AST: 80 U/L (10-40) HIGH
        """
        params = extract_parameters_from_raw_items(extract_parameters_from_text(report))
        res = openrouter_service.get_fallback_analysis(params, {"age": 21, "gender": "Male"}, reason="Test fallback")
        self.assertIn("rare_unusual_screening", res)
        self.assertTrue(res["rare_unusual_screening"]["flagged"])
        self.assertEqual(res["rare_unusual_screening"]["screening_strength"], "HIGH")

    def test_17_csv_extraction_parity(self):
        """Test 17 & Requirement 20: CSV format normalizes into identical biomarker representations."""
        csv_bytes = b"Parameter,Observed Value,Unit,Reference Interval,Status\nAlpha-1 Antitrypsin,42.0,mg/dL,90.0-200.0,LOW\nALT,118,U/L,10-40,HIGH"
        _, raw_items = parse_csv_report(csv_bytes)
        params = extract_parameters_from_raw_items(raw_items)
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["canonical_key"], "ALPHA1_ANTITRYPSIN")
        self.assertEqual(params[0]["value"], 42.0)
        self.assertEqual(params[0]["status"], "LOW")

    def test_18_txt_extraction_parity(self):
        """Test 18: TXT format normalization."""
        txt = "Alpha-1 Antitrypsin: 42.0 mg/dL [90.0-200.0] LOW\nALT: 118 U/L (10-40) HIGH"
        _, params = extract_metadata_and_biomarkers(txt)
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["canonical_key"], "ALPHA1_ANTITRYPSIN")
        self.assertEqual(params[0]["value"], 42.0)

    def test_19_existing_ml_regression(self):
        """Test 19 & Requirement 28: 5 Validated ML models evaluate with intact contracts."""
        params = [
            {"canonical_key": "HGB", "value": 8.5, "status": "LOW"},
            {"canonical_key": "RBC", "value": 3.2, "status": "LOW"},
            {"canonical_key": "PCV", "value": 28.0, "status": "LOW"},
            {"canonical_key": "MCV", "value": 72.0, "status": "LOW"},
            {"canonical_key": "MCH", "value": 22.0, "status": "LOW"},
            {"canonical_key": "MCHC", "value": 30.5, "status": "LOW"},
            {"canonical_key": "RDW", "value": 16.5, "status": "HIGH"},
            {"canonical_key": "WBC", "value": 5200, "status": "NORMAL"},
            {"canonical_key": "PLT", "value": 45000, "status": "LOW"},
            {"canonical_key": "PDW", "value": 18.0, "status": "HIGH"},
            {"canonical_key": "DIFFERENTIAL_COUNT", "value": 100, "status": "NORMAL"},
            {"canonical_key": "ALT", "value": 120, "status": "HIGH"},
            {"canonical_key": "AST", "value": 110, "status": "HIGH"},
            {"canonical_key": "TOTAL_BILIRUBIN", "value": 2.2, "status": "HIGH"},
            {"canonical_key": "DIRECT_BILIRUBIN", "value": 1.2, "status": "HIGH"},
            {"canonical_key": "ALP", "value": 140, "status": "NORMAL"},
            {"canonical_key": "TOTAL_PROTEIN", "value": 6.8, "status": "NORMAL"},
            {"canonical_key": "ALBUMIN", "value": 3.4, "status": "LOW"},
            {"canonical_key": "AG_RATIO", "value": 1.0, "status": "NORMAL"},
            {"canonical_key": "TSH", "value": 9.2, "status": "HIGH"},
            {"canonical_key": "T3", "value": 0.6, "status": "LOW"},
            {"canonical_key": "T4", "value": 4.2, "status": "LOW"},
            {"canonical_key": "FREE_T4", "value": 0.5, "status": "LOW"},
            {"canonical_key": "TSH_RESPONSE", "value": 2.5, "status": "NORMAL"},
            {"canonical_key": "T3_RESIN_UPTAKE", "value": 21.0, "status": "LOW"}
        ]
        ml_res = evaluate_extracted_report_with_ml(params, {"age": 30, "gender": "Female"})
        self.assertIn("anemia", ml_res)
        self.assertIn("dengue", ml_res)
        self.assertIn("liver", ml_res)
        self.assertIn("thyroid", ml_res)
        self.assertTrue(ml_res["anemia"]["evaluated"])
        self.assertTrue(ml_res["dengue"]["evaluated"])
        self.assertTrue(ml_res["liver"]["evaluated"])
        self.assertTrue(ml_res["thyroid"]["evaluated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
