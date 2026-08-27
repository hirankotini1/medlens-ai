"""
Comprehensive Verification Suite for G6PD Biomarker Extraction,
Platelet Numeric Preservation, and Rare-Disease Mapping Invariants.

Tests:
- TEST 1: G6PD PDF Extraction & Screening (G6PD = 2.1 U/g Hb LOW -> G6PD Deficiency HIGH, No 'Not available' message)
- TEST 2: Generic Hemolysis WITHOUT G6PD (Flags Hemolytic Anemia, G6PD NOT HIGH)
- TEST 3: Normal G6PD Activity (G6PD = 12.5 U/g Hb NORMAL -> G6PD NOT HIGH)
- TEST 4: Platelet Count Numeric Value (205000 stays 205000, 205,000 stays 205000)
- TEST 5: Wilson Disease Pattern (Unchanged & verified)
- TEST 6: Hemochromatosis Pattern (Unchanged & verified)
- TEST 7: Alpha-1 Antitrypsin Pattern (Unchanged & verified)
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from disease_prediction.api.report_extractor import (
    extract_parameters_from_text,
    extract_parameters_from_raw_items,
    calculate_report_data_quality
)
from disease_prediction.api import rare_disease_engine


class TestG6PDAndPlateletFix(unittest.TestCase):

    def test_01_g6pd_pdf_extraction_and_screening(self):
        """TEST 1: G6PD PDF extracts G6PD Enzyme Activity = 2.1 U/g Hb LOW and produces HIGH screening signal."""
        raw_text = """
        ========================================================================================
        PARAMETER                      OBSERVED VALUE   UNIT         REFERENCE RANGE   STATUS
        ========================================================================================
        G6PD Enzyme Activity           2.1              U/g Hb       7.0 - 10.5        LOW
        LDH                            610.0            U/L          140 - 280         HIGH
        Haptoglobin                    16.0             mg/dL        30 - 200          LOW
        Indirect Bilirubin             3.5              mg/dL        0.1 - 0.8         HIGH
        Reticulocyte Count             6.1              %            0.5 - 2.5         HIGH
        Hemoglobin                     10.8             g/dL         12.0 - 16.0       LOW
        Platelet Count                 205000           /uL          150000 - 450000   NORMAL
        ========================================================================================
        """
        raw_items = extract_parameters_from_text(raw_text)
        params = extract_parameters_from_raw_items(raw_items)
        param_map = {p["canonical_key"]: p for p in params}

        # 1. Extraction checks
        self.assertIn("G6PD_ENZYME_ACTIVITY", param_map)
        g6pd_param = param_map["G6PD_ENZYME_ACTIVITY"]
        self.assertEqual(g6pd_param["value"], 2.1)
        self.assertEqual(g6pd_param["status"], "LOW")
        self.assertIn("U/g", g6pd_param["unit"])

        # 2. Screening engine evaluation
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 25, "gender": "Male"})
        self.assertTrue(res["flagged"])

        top_cond = res["top_condition"]
        self.assertIsNotNone(top_cond)
        self.assertIn("g6pd_deficiency", [c["disease_id"] for c in res["conditions"]])
        
        g6pd_res = next(c for c in res["conditions"] if c["disease_id"] == "g6pd_deficiency")
        self.assertEqual(g6pd_res["screening_strength"], "HIGH")
        self.assertGreaterEqual(g6pd_res["concordance_pct"], 75)

        # 3. Invariant check: G6PD must NOT be in unsupported conditions with "Not available in report"
        for uc in res.get("unsupported_conditions", []):
            if uc["disease_id"] == "g6pd_deficiency":
                for ec in uc.get("evidence_checked", []):
                    self.assertNotIn("Not available", ec.get("status_text", ""))

    def test_02_generic_hemolysis_without_g6pd(self):
        """TEST 2: Generic hemolysis WITHOUT G6PD enzyme result produces Hemolytic Anemia Pattern, NOT G6PD."""
        hemo_text = """
        LDH: 640 U/L (140 - 280) HIGH
        Haptoglobin: 14 mg/dL (30 - 200) LOW
        Indirect Bilirubin: 3.2 mg/dL (0.1 - 0.8) HIGH
        Reticulocyte Count: 5.8 % (0.5 - 2.5) HIGH
        Hemoglobin: 9.6 g/dL (12.0 - 16.0) LOW
        """
        raw_items = extract_parameters_from_text(hemo_text)
        params = extract_parameters_from_raw_items(raw_items)
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 28, "gender": "Male"})
        
        self.assertTrue(res["flagged"])
        flagged_ids = [c["disease_id"] for c in res["conditions"]]
        self.assertIn("hemolytic_anemia_generic", flagged_ids)
        
        # G6PD must NOT be HIGH because enzyme assay is missing
        g6pd_cand = next((c for c in res["conditions"] if c["disease_id"] == "g6pd_deficiency"), None)
        if g6pd_cand:
            self.assertNotEqual(g6pd_cand["screening_strength"], "HIGH")

    def test_03_normal_g6pd_activity(self):
        """TEST 3: Normal G6PD enzyme activity (12.5 U/g Hb) contradicts and rejects G6PD deficiency."""
        normal_g6pd_text = """
        G6PD Enzyme Activity: 12.5 U/g Hb (7.0 - 10.5) NORMAL
        LDH: 580 U/L (140 - 280) HIGH
        Haptoglobin: 18 mg/dL (30 - 200) LOW
        Indirect Bilirubin: 2.8 mg/dL (0.1 - 0.8) HIGH
        Reticulocyte Count: 4.5 % (0.5 - 2.5) HIGH
        """
        raw_items = extract_parameters_from_text(normal_g6pd_text)
        params = extract_parameters_from_raw_items(raw_items)
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 30, "gender": "Male"})
        
        g6pd_cand = next((c for c in res["conditions"] if c["disease_id"] == "g6pd_deficiency"), None)
        self.assertIsNone(g6pd_cand, "Normal G6PD should contradict G6PD deficiency from evaluated candidates")

    def test_04_platelet_count_numeric_preservation(self):
        """TEST 4: Platelet count 205000 must remain 205000 with zero truncation or dropped digits."""
        test_lines = [
            "Platelet Count            205000       /uL       150000 - 450000      NORMAL",
            "Platelet Count: 205000 /uL (150000 - 450000) NORMAL",
            "Platelet Count: 205,000 /uL (150,000 - 450,000) NORMAL",
            "Platelet Count 205000 /uL 150000 - 450000 NORMAL"
        ]
        for line in test_lines:
            items = extract_parameters_from_text(line)
            self.assertEqual(len(items), 1, f"Failed on line: {line}")
            self.assertEqual(items[0]["canonical_key"], "PLT")
            self.assertEqual(items[0]["value"], 205000.0, f"Value was corrupted on line: {line}")

    def test_05_wilson_disease_unaltered(self):
        """TEST 5: Wilson disease pattern remains fully functional and high strength."""
        wilson_text = """
        Ceruloplasmin: 8.5 mg/dL (20 - 40) LOW
        24-Hour Urinary Copper: 145.0 ug/24h (15 - 60) HIGH
        Serum Copper: 42.0 ug/dL (70 - 140) LOW
        ALT: 185.0 U/L (10 - 40) HIGH
        AST: 140.0 U/L (10 - 40) HIGH
        Total Bilirubin: 2.8 mg/dL (0.2 - 1.2) HIGH
        """
        raw_items = extract_parameters_from_text(wilson_text)
        params = extract_parameters_from_raw_items(raw_items)
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 22, "gender": "Male"})
        self.assertTrue(res["flagged"])
        wilson_cond = next((c for c in res["conditions"] if c["disease_id"] == "wilson_disease"), None)
        self.assertIsNotNone(wilson_cond)
        self.assertEqual(wilson_cond["screening_strength"], "HIGH")

    def test_06_hemochromatosis_unaltered(self):
        """TEST 6: Hereditary Hemochromatosis pattern remains fully functional."""
        hemo_text = """
        Transferrin Saturation: 78.0 % (20 - 50) HIGH
        Ferritin: 1250.0 ng/mL (30 - 400) HIGH
        Serum Iron: 215.0 ug/dL (60 - 170) HIGH
        ALT: 88.0 U/L (10 - 40) HIGH
        AST: 72.0 U/L (10 - 40) HIGH
        """
        raw_items = extract_parameters_from_text(hemo_text)
        params = extract_parameters_from_raw_items(raw_items)
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 45, "gender": "Male"})
        self.assertTrue(res["flagged"])
        hemo_cond = next((c for c in res["conditions"] if c["disease_id"] == "hemochromatosis"), None)
        self.assertIsNotNone(hemo_cond)
        self.assertEqual(hemo_cond["screening_strength"], "HIGH")

    def test_07_alpha1_antitrypsin_unaltered(self):
        """TEST 7: Alpha-1 Antitrypsin Deficiency pattern remains fully functional."""
        aat_text = """
        Alpha-1 Antitrypsin: 42.0 mg/dL (90 - 200) LOW
        ALT: 118.0 U/L (10 - 40) HIGH
        AST: 96.0 U/L (10 - 40) HIGH
        Total Bilirubin: 1.8 mg/dL (0.2 - 1.2) HIGH
        Albumin: 3.2 g/dL (3.5 - 5.0) LOW
        """
        raw_items = extract_parameters_from_text(aat_text)
        params = extract_parameters_from_raw_items(raw_items)
        res = rare_disease_engine.evaluate_rare_disease_patterns(params, {"age": 42, "gender": "Female"})
        self.assertTrue(res["flagged"])
        aat_cond = next((c for c in res["conditions"] if c["disease_id"] == "alpha1_antitrypsin_deficiency"), None)
        self.assertIsNotNone(aat_cond)
        self.assertEqual(aat_cond["screening_strength"], "HIGH")

    def test_08_data_quality_reference_ranges_count(self):
        """TEST 8: Data quality metrics accurately count extracted reference ranges."""
        text = """
        Hemoglobin: 14.2 g/dL (12.0 - 16.0) NORMAL
        WBC Count: 6800 /uL (4000 - 11000) NORMAL
        Platelet Count: 205000 /uL (150000 - 450000) NORMAL
        G6PD Enzyme Activity: 2.1 U/g Hb (7.0 - 10.5) LOW
        """
        raw_items = extract_parameters_from_text(text)
        params = extract_parameters_from_raw_items(raw_items)
        dq = calculate_report_data_quality({}, params)
        self.assertEqual(dq["biomarkers_detected"], 4)
        self.assertEqual(dq["reference_ranges_detected"], 4)
        self.assertEqual(dq["reference_intervals_detected"], 4)
        self.assertEqual(dq["unmapped_parameters"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
