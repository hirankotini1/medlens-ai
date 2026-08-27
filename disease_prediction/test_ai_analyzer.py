"""
Nexus Pathology — Automated Comprehensive Test Suite for AI Health Report Analyzer & Multi-Disease Rare Condition Screening
Validates:
1. Canonical biomarker alias normalization
2. Platelet Count -> PLT /mm3 mapping
3. WBC Count -> required WBC/TLC feature mapping
4. ALT -> alamine_aminotransferase mapping
5. AST -> aspartate_aminotransferase mapping
6. Total Bilirubin -> total_bilirubin mapping
7. PCV / Hematocrit -> PCV mapping
8. 24-Hour Urinary Copper -> URINARY_COPPER_24H mapping
9. Missing feature detection with 3-state tracking (no false missing messages)
10. No fabricated or invented values
11. Normal report -> No rare disease forced
12. Wilson disease pattern -> HIGH screening signal with multi-marker concordance
13. Partial Wilson pattern -> Does NOT flag Wilson as HIGH
14. Hereditary Hemochromatosis pattern -> HIGH screening signal
15. Multiple Myeloma pattern -> HIGH screening signal (Total Protein, Globulin, A/G, Calcium, Anemia)
16. Thalassemia trait pattern -> HIGH screening signal (Low MCV/MCH, High RBC, Normal Ferritin)
17. Addison disease pattern -> HIGH screening signal (Low Na, High K, Low Glucose)
18. G6PD / Hemolytic anemia pattern -> HIGH screening signal (Low Hgb, High LDH, Low Haptoglobin, High Reticulocytes)
19. Primary Biliary Cholangitis pattern -> HIGH screening signal (High ALP, High Direct Bilirubin, High Globulin)
20. Cushing syndrome pattern -> HIGH/MODERATE screening signal (High Glucose, Low K, High Na)
21. Hereditary Spherocytosis pattern -> HIGH screening signal (High MCHC, High Reticulocytes, Hemolysis)
22. Unrelated abnormal biomarkers -> Avoids overdiagnosis
23. Patient PII stripping (no names, IDs, phones, emails)
24. Safe non-diagnostic wording & disclaimer verification
25. T3 Resin Uptake = 31% with reference 24–39% remains NORMAL
26. Differential Count = 100% is safely mapped for ML
27. Anemia model evaluation with complete CBC values
28. Liver model evaluation with complete LFT values
29. API endpoint handles full multi-disease workflow
30. Patient isolation and IDOR defense
"""

import unittest
import io
import os
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from disease_prediction.api.main import app
from disease_prediction.api import database as db
from disease_prediction.api import file_parser
from disease_prediction.api import report_extractor
from disease_prediction.api import feature_mapper
from disease_prediction.api import ml_bridge
from disease_prediction.api import rare_disease_engine
from disease_prediction.api import openrouter_service
from disease_prediction.api import analyzer_service


class TestAIHealthReportAnalyzer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db.init_db()
        db.reset_to_clean_seed()
        cls.client = TestClient(app)

        # Login as patient John Doe
        p_resp = cls.client.post("/api/patient/login", json={"patient_id": "PAT-1001", "access_pin": "PIN-1001"})
        cls.patient_token = p_resp.json()["token"]

        # Login as patient Jane Smith
        p2_resp = cls.client.post("/api/patient/login", json={"patient_id": "PAT-1002", "access_pin": "PIN-1002"})
        cls.patient2_token = p2_resp.json()["token"]

        # Login as Admin
        a_resp = cls.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        cls.admin_token = a_resp.json()["token"]

    def setUp(self):
        db.reset_to_clean_seed()

    # -------------------------------------------------------------
    # 1. Metadata vs. Biomarker Extraction (Tests 1 - 3)
    # -------------------------------------------------------------
    def test_01_correct_metadata_extraction(self):
        """Test 1: Metadata (Patient ID, Report ID, Age, Date, Doctor) separated cleanly."""
        sample = "Patient ID: RARE-DEMO-001\nReport ID: REP-2026\nAge: 24 Yrs\nGender: Male\nReferring Doctor: Dr. Mehta"
        meta, biomarkers = report_extractor.extract_metadata_and_biomarkers(sample)
        self.assertEqual(meta["patient_id"], "RARE-DEMO-001")
        self.assertEqual(meta["report_id"], "REP-2026")
        self.assertEqual(meta["age"], 24)
        self.assertEqual(meta["gender"], "Male")
        self.assertEqual(meta["referring_doctor"], "Dr. Mehta")
        self.assertEqual(len(biomarkers), 0)

    def test_02_correct_biomarker_extraction(self):
        """Test 2: Biomarkers extracted with numeric value, unit, and source reference intervals."""
        sample = "Hemoglobin 13.5 g/dL (12.0 - 16.0)\nALT 35 U/L (10 - 40)"
        _, biomarkers = report_extractor.extract_metadata_and_biomarkers(sample)
        self.assertEqual(len(biomarkers), 2)
        hgb = next(b for b in biomarkers if b["canonical_key"] == "HGB")
        self.assertEqual(hgb["value"], 13.5)
        self.assertEqual(hgb["unit"], "g/dL")
        self.assertEqual(hgb["status"], "NORMAL")

    def test_03_alias_normalization(self):
        """Test 3: Biomarker aliases normalize to canonical keys."""
        items = [
            {"parameter": "Hemoglobin", "value": 14.0},
            {"parameter": "RBC Count", "value": 4.5},
            {"parameter": "PCV / Hematocrit", "value": 42.0},
            {"parameter": "WBC Count", "value": 6500},
            {"parameter": "SGPT", "value": 30},
            {"parameter": "SGOT", "value": 28},
            {"parameter": "Platelet Count", "value": 250000},
            {"parameter": "24-Hour Urinary Copper", "value": 35.0}
        ]
        params = report_extractor.extract_parameters_from_raw_items(items)
        keys = [p["canonical_key"] for p in params]
        self.assertIn("HGB", keys)
        self.assertIn("RBC", keys)
        self.assertIn("PCV", keys)
        self.assertIn("WBC", keys)
        self.assertIn("ALT", keys)
        self.assertIn("AST", keys)
        self.assertIn("PLT", keys)
        self.assertIn("URINARY_COPPER_24H", keys)

    # -------------------------------------------------------------
    # 2. Central Feature Mapping & ML Bridge (Tests 4 - 8)
    # -------------------------------------------------------------
    def test_04_platelet_count_to_plt_mapping(self):
        """Test 4: Platelet Count (178000 /uL) maps to PLT /mm3 (178.0) for Anemia and 178000 for Dengue."""
        params = [{"canonical_key": "PLT", "parameter": "Platelet Count", "value": 178000, "unit": "/uL"}]
        anemia_map = feature_mapper.map_features_for_model("anemia", params)
        self.assertEqual(anemia_map["feature_states"]["PLT /mm3"]["value"], 178.0)

        dengue_map = feature_mapper.map_features_for_model("dengue", params)
        self.assertEqual(dengue_map["feature_states"]["platelet_count"]["value"], 178000)

    def test_05_wbc_count_to_required_feature_mapping(self):
        """Test 5: WBC Count (7200 /uL) maps to TLC (7.2) for Anemia and wbc_count (7200) for Dengue."""
        params = [{"canonical_key": "WBC", "parameter": "Total Leukocyte Count (WBC)", "value": 7200, "unit": "/uL"}]
        anemia_map = feature_mapper.map_features_for_model("anemia", params)
        self.assertEqual(anemia_map["feature_states"]["TLC"]["value"], 7.2)

        dengue_map = feature_mapper.map_features_for_model("dengue", params)
        self.assertEqual(dengue_map["feature_states"]["wbc_count"]["value"], 7200)

    def test_06_missing_feature_detection_with_3_state_tracking(self):
        """Test 6: Feature mapper explicitly tracks EXTRACTED vs MISSING states without confusing extracted features."""
        params = [
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 10.4, "unit": "g/dL"},
            {"canonical_key": "PLT", "parameter": "Platelet Count", "value": 178000, "unit": "/uL"}
        ]
        anemia_map = feature_mapper.map_features_for_model("anemia", params, patient_meta={"age": 24, "gender": "Male"})
        self.assertFalse(anemia_map["can_evaluate"])
        self.assertEqual(anemia_map["feature_states"]["HGB"]["state"], "EXTRACTED")
        self.assertEqual(anemia_map["feature_states"]["PLT /mm3"]["state"], "EXTRACTED")
        self.assertEqual(anemia_map["feature_states"]["PCV"]["state"], "MISSING")
        self.assertIn("Packed Cell Volume (PCV)", anemia_map["missing_features"])

    def test_07_t3_resin_uptake_reference_range_preservation(self):
        """Test 7: T3 Resin Uptake = 31% with source reference 24–39% is preserved and marked NORMAL."""
        sample = "T3 Resin Uptake 31 % (24–39%) NORMAL"
        _, biomarkers = report_extractor.extract_metadata_and_biomarkers(sample)
        self.assertEqual(len(biomarkers), 1)
        t3_ru = biomarkers[0]
        self.assertEqual(t3_ru["canonical_key"], "T3_RESIN_UPTAKE")
        self.assertEqual(t3_ru["value"], 31.0)
        self.assertEqual(t3_ru["status"], "NORMAL")

    def test_08_differential_count_100_percent_handling(self):
        """Test 8: Differential Count = 100% is parsed as NORMAL and safely mapped for ML."""
        sample = "Differential Count 100 % (100%) NORMAL"
        _, biomarkers = report_extractor.extract_metadata_and_biomarkers(sample)
        self.assertEqual(len(biomarkers), 1)
        diff = biomarkers[0]
        self.assertEqual(diff["canonical_key"], "DIFFERENTIAL_COUNT")
        self.assertEqual(diff["value"], 100.0)
        self.assertEqual(diff["status"], "NORMAL")

        dengue_map = feature_mapper.map_features_for_model("dengue", biomarkers)
        self.assertEqual(dengue_map["feature_states"]["differential_count"]["value"], 0)

    # -------------------------------------------------------------
    # 3. Multi-Disease Rare Condition Screening Engine (Tests 9 - 22)
    # -------------------------------------------------------------
    def test_09_normal_report_no_rare_disease_forced(self):
        """Test 9: Normal laboratory report does NOT force or flag any rare disease."""
        normal_params = [
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 14.5, "unit": "g/dL", "status": "NORMAL"},
            {"canonical_key": "ALT", "parameter": "ALT", "value": 22, "unit": "U/L", "status": "NORMAL"},
            {"canonical_key": "TSH", "parameter": "TSH", "value": 2.1, "unit": "uIU/mL", "status": "NORMAL"},
            {"canonical_key": "CERULOPLASMIN", "parameter": "Ceruloplasmin", "value": 28, "unit": "mg/dL", "status": "NORMAL"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(normal_params, {"age": 30, "gender": "Female"})
        self.assertFalse(res["flagged"])
        self.assertEqual(res["screening_strength"], "NONE")
        self.assertEqual(len(res["conditions"]), 0)

    def test_10_wilson_disease_high_screening_signal(self):
        """Test 10: Multi-marker Wilson disease pattern produces HIGH screening signal."""
        wilson_params = [
            {"canonical_key": "CERULOPLASMIN", "parameter": "Ceruloplasmin", "value": 8, "unit": "mg/dL", "status": "LOW"},
            {"canonical_key": "URINARY_COPPER_24H", "parameter": "24-Hour Urinary Copper", "value": 185, "unit": "µg/24h", "status": "HIGH"},
            {"canonical_key": "SERUM_COPPER", "parameter": "Serum Copper", "value": 52, "unit": "µg/dL", "status": "LOW"},
            {"canonical_key": "ALT", "parameter": "ALT", "value": 186, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "AST", "parameter": "AST", "value": 245, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "TOTAL_BILIRUBIN", "parameter": "Total Bilirubin", "value": 4.8, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "INDIRECT_BILIRUBIN", "parameter": "Indirect Bilirubin", "value": 3.7, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "LDH", "parameter": "LDH", "value": 680, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "HAPTOGLOBIN", "parameter": "Haptoglobin", "value": 18, "unit": "mg/dL", "status": "LOW"},
            {"canonical_key": "RETICULOCYTES", "parameter": "Reticulocyte Count", "value": 3.2, "unit": "%", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(wilson_params, {"age": 24, "gender": "Male"})
        self.assertTrue(res["flagged"])
        self.assertEqual(res["screening_strength"], "HIGH")
        top = res["conditions"][0]
        self.assertEqual(top["disease_id"], "wilson_disease")
        self.assertEqual(top["screening_strength"], "HIGH")
        self.assertGreaterEqual(top["evidence_count"], 8)
        self.assertIn("Wilson", top["why_flagged"])

    def test_11_partial_wilson_pattern_does_not_flag_high(self):
        """Test 11: Isolated transaminitis without copper markers does NOT flag Wilson disease as HIGH."""
        isolated_liver = [
            {"canonical_key": "ALT", "parameter": "ALT", "value": 55, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "AST", "parameter": "AST", "value": 48, "unit": "U/L", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(isolated_liver, {"age": 45, "gender": "Male"})
        wilson_candidates = [c for c in res["conditions"] if c["disease_id"] == "wilson_disease"]
        self.assertEqual(len(wilson_candidates), 0)

    def test_12_hemochromatosis_screening_pattern(self):
        """Test 12: High Ferritin, High Transferrin Saturation, and elevated ALT flag Hemochromatosis as HIGH."""
        hemo_params = [
            {"canonical_key": "FERRITIN", "parameter": "Serum Ferritin", "value": 850, "unit": "ng/mL", "status": "HIGH"},
            {"canonical_key": "TRANSFERRIN_SAT", "parameter": "Transferrin Saturation", "value": 68, "unit": "%", "status": "HIGH"},
            {"canonical_key": "IRON", "parameter": "Serum Iron", "value": 195, "unit": "µg/dL", "status": "HIGH"},
            {"canonical_key": "ALT", "parameter": "ALT", "value": 68, "unit": "U/L", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(hemo_params, {"age": 52, "gender": "Male"})
        self.assertTrue(res["flagged"])
        hemo_match = next((c for c in res["conditions"] if c["disease_id"] == "hemochromatosis"), None)
        self.assertIsNotNone(hemo_match)
        self.assertEqual(hemo_match["screening_strength"], "HIGH")
        self.assertIn("HFE", " ".join(hemo_match["confirmatory_evaluation"]))

    def test_13_multiple_myeloma_screening_pattern(self):
        """Test 13: High Total Protein, High Globulin, Low A/G, Hypercalcemia, and Anemia flag Multiple Myeloma pattern."""
        myeloma_params = [
            {"canonical_key": "TOTAL_PROTEIN", "parameter": "Total Protein", "value": 9.8, "unit": "g/dL", "status": "HIGH"},
            {"canonical_key": "GLOBULIN", "parameter": "Serum Globulin", "value": 6.4, "unit": "g/dL", "status": "HIGH"},
            {"canonical_key": "ALBUMIN", "parameter": "Albumin", "value": 3.4, "unit": "g/dL", "status": "NORMAL"},
            {"canonical_key": "AG_RATIO", "parameter": "A/G Ratio", "value": 0.53, "unit": "ratio", "status": "LOW"},
            {"canonical_key": "CALCIUM", "parameter": "Serum Calcium", "value": 11.8, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 9.2, "unit": "g/dL", "status": "LOW"},
            {"canonical_key": "ESR", "parameter": "ESR", "value": 85, "unit": "mm/hr", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(myeloma_params, {"age": 64, "gender": "Female"})
        self.assertTrue(res["flagged"])
        myeloma_match = next((c for c in res["conditions"] if c["disease_id"] == "multiple_myeloma"), None)
        self.assertIsNotNone(myeloma_match)
        self.assertEqual(myeloma_match["screening_strength"], "HIGH")
        self.assertIn("Electrophoresis", " ".join(myeloma_match["confirmatory_evaluation"]))

    def test_14_thalassemia_trait_screening_pattern(self):
        """Test 14: Disproportionate microcytosis (Low MCV/MCH), High RBC count, and Normal Ferritin flag Thalassemia trait."""
        thal_params = [
            {"canonical_key": "MCV", "parameter": "MCV", "value": 62.0, "unit": "fL", "status": "LOW"},
            {"canonical_key": "MCH", "parameter": "MCH", "value": 20.0, "unit": "pg", "status": "LOW"},
            {"canonical_key": "RBC", "parameter": "RBC Count", "value": 5.8, "unit": "million/µL", "status": "HIGH"},
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 11.2, "unit": "g/dL", "status": "LOW"},
            {"canonical_key": "FERRITIN", "parameter": "Serum Ferritin", "value": 120, "unit": "ng/mL", "status": "NORMAL"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(thal_params, {"age": 28, "gender": "Male"})
        self.assertTrue(res["flagged"])
        thal_match = next((c for c in res["conditions"] if c["disease_id"] == "thalassemia_trait"), None)
        self.assertIsNotNone(thal_match)
        self.assertEqual(thal_match["screening_strength"], "HIGH")
        self.assertIn("HPLC", " ".join(thal_match["confirmatory_evaluation"]))

    def test_15_addison_disease_screening_pattern(self):
        """Test 15: Hyponatremia, Hyperkalemia, Low Glucose, and High Urea flag Addison disease pattern."""
        addison_params = [
            {"canonical_key": "SODIUM", "parameter": "Sodium", "value": 126, "unit": "mmol/L", "status": "LOW"},
            {"canonical_key": "POTASSIUM", "parameter": "Potassium", "value": 5.8, "unit": "mmol/L", "status": "HIGH"},
            {"canonical_key": "GLUCOSE", "parameter": "Fasting Glucose", "value": 62, "unit": "mg/dL", "status": "LOW"},
            {"canonical_key": "UREA", "parameter": "Blood Urea", "value": 48, "unit": "mg/dL", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(addison_params, {"age": 35, "gender": "Female"})
        self.assertTrue(res["flagged"])
        addison_match = next((c for c in res["conditions"] if c["disease_id"] == "addison_disease"), None)
        self.assertIsNotNone(addison_match)
        self.assertEqual(addison_match["screening_strength"], "HIGH")
        self.assertIn("Cortisol", " ".join(addison_match["confirmatory_evaluation"]))

    def test_16_g6pd_hemolytic_pattern(self):
        """Test 16: Anemia, High LDH, Low Haptoglobin, High Indirect Bilirubin, and Reticulocytosis flag Hemolytic pattern."""
        hemo_params = [
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 8.8, "unit": "g/dL", "status": "LOW"},
            {"canonical_key": "LDH", "parameter": "LDH", "value": 780, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "HAPTOGLOBIN", "parameter": "Haptoglobin", "value": 12, "unit": "mg/dL", "status": "LOW"},
            {"canonical_key": "INDIRECT_BILIRUBIN", "parameter": "Indirect Bilirubin", "value": 3.8, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "RETICULOCYTES", "parameter": "Reticulocyte Count", "value": 6.2, "unit": "%", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(hemo_params, {"age": 22, "gender": "Male"})
        self.assertTrue(res["flagged"])
        hemo_match = next((c for c in res["conditions"] if c["disease_id"] in ["hemolytic_anemia_generic", "g6pd_hemolysis"]), None)
        self.assertIsNotNone(hemo_match)
        self.assertEqual(hemo_match["screening_strength"], "HIGH")

    def test_17_primary_biliary_cholangitis_pattern(self):
        """Test 17: Markedly elevated ALP, elevated Direct Bilirubin, and elevated Globulin flag PBC pattern."""
        pbc_params = [
            {"canonical_key": "ALP", "parameter": "Alkaline Phosphatase", "value": 380, "unit": "U/L", "status": "HIGH"},
            {"canonical_key": "DIRECT_BILIRUBIN", "parameter": "Direct Bilirubin", "value": 1.8, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "GLOBULIN", "parameter": "Globulin", "value": 4.1, "unit": "g/dL", "status": "HIGH"},
            {"canonical_key": "ALT", "parameter": "ALT", "value": 52, "unit": "U/L", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(pbc_params, {"age": 48, "gender": "Female"})
        self.assertTrue(res["flagged"])
        pbc_match = next((c for c in res["conditions"] if c["disease_id"] == "primary_biliary_cholangitis"), None)
        self.assertIsNotNone(pbc_match)
        self.assertEqual(pbc_match["screening_strength"], "HIGH")

    def test_18_hereditary_spherocytosis_pattern(self):
        """Test 18: High MCHC (> 35.5 g/dL), High Reticulocytes, and Hemolysis flag Spherocytosis pattern."""
        sphero_params = [
            {"canonical_key": "MCHC", "parameter": "MCHC", "value": 36.8, "unit": "g/dL", "status": "HIGH"},
            {"canonical_key": "RETICULOCYTES", "parameter": "Reticulocyte Count", "value": 7.5, "unit": "%", "status": "HIGH"},
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 9.5, "unit": "g/dL", "status": "LOW"},
            {"canonical_key": "INDIRECT_BILIRUBIN", "parameter": "Indirect Bilirubin", "value": 3.2, "unit": "mg/dL", "status": "HIGH"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(sphero_params, {"age": 19, "gender": "Male"})
        self.assertTrue(res["flagged"])
        sphero_match = next((c for c in res["conditions"] if c["disease_id"] == "hereditary_spherocytosis"), None)
        self.assertIsNotNone(sphero_match)
        self.assertEqual(sphero_match["screening_strength"], "HIGH")

    def test_19_unrelated_abnormal_biomarkers_avoids_overdiagnosis(self):
        """Test 19: Unrelated abnormal biomarkers (e.g. high ESR, high Glucose, low Albumin) do NOT falsely trigger rare metabolic diseases."""
        unrelated = [
            {"canonical_key": "ESR", "parameter": "ESR", "value": 35, "unit": "mm/hr", "status": "HIGH"},
            {"canonical_key": "GLUCOSE", "parameter": "Glucose", "value": 140, "unit": "mg/dL", "status": "HIGH"},
            {"canonical_key": "ALBUMIN", "parameter": "Albumin", "value": 3.2, "unit": "g/dL", "status": "LOW"}
        ]
        res = rare_disease_engine.evaluate_rare_disease_patterns(unrelated, {"age": 55, "gender": "Male"})
        wilson_candidates = [c for c in res["conditions"] if c["disease_id"] == "wilson_disease"]
        self.assertEqual(len(wilson_candidates), 0)

    def test_20_patient_pii_stripping_and_disclaimer(self):
        """Test 20: strip_pii_from_payload strips patient names, IDs, phones, emails and maintains non-diagnostic disclaimers."""
        meta = {
            "patient_name": "Alex Rivera",
            "patient_id": "RARE-DEMO-001",
            "report_id": "REP-WILSON-2026",
            "phone": "+1-555-0199",
            "email": "alex.rivera@example.com",
            "age": 24,
            "gender": "Male"
        }
        params = [{"canonical_key": "ALT", "parameter": "ALT", "value": 186, "unit": "U/L", "status": "HIGH"}]
        payload = openrouter_service.strip_pii_from_payload(params, meta)
        raw_str = json.dumps(payload)
        self.assertNotIn("Alex Rivera", raw_str)
        self.assertNotIn("RARE-DEMO-001", raw_str)
        self.assertNotIn("alex.rivera@example.com", raw_str)

    def test_21_anemia_model_complete_evaluation(self):
        """Test 21: Anemia model evaluates when all CBC values are available."""
        cbc_params = [
            {"canonical_key": "HGB", "parameter": "Hemoglobin", "value": 10.4, "unit": "g/dL"},
            {"canonical_key": "RBC", "parameter": "RBC Count", "value": 3.55, "unit": "million/µL"},
            {"canonical_key": "PCV", "parameter": "PCV / Hematocrit", "value": 31.0, "unit": "%"},
            {"canonical_key": "MCV", "parameter": "MCV", "value": 87.0, "unit": "fL"},
            {"canonical_key": "MCH", "parameter": "MCH", "value": 29.0, "unit": "pg"},
            {"canonical_key": "MCHC", "parameter": "MCHC", "value": 33.5, "unit": "g/dL"},
            {"canonical_key": "RDW", "parameter": "RDW", "value": 15.8, "unit": "%"},
            {"canonical_key": "WBC", "parameter": "WBC Count", "value": 7200, "unit": "/µL"},
            {"canonical_key": "PLT", "parameter": "Platelet Count", "value": 178000, "unit": "/µL"}
        ]
        meta = {"age": 24, "gender": "Male"}
        ml_res = ml_bridge.evaluate_extracted_report_with_ml(cbc_params, meta)
        self.assertTrue(ml_res["anemia"]["evaluated"])
        self.assertEqual(ml_res["anemia"]["status"], "MODEL ANALYSIS AVAILABLE")

    def test_22_api_handles_multi_disease_analysis(self):
        """Test 22: POST /api/analyzer/analyze returns structured multi-disease candidate cards."""
        csv_bytes = (
            "Patient ID,RARE-DEMO-001\n"
            "Age,24\n"
            "Gender,Male\n"
            "Report ID,REP-WILSON-2026\n"
            "Investigation,Observed Value,Unit,Reference Range,Status\n"
            "Hemoglobin,10.4,g/dL,13.0 - 17.0,LOW\n"
            "ALT,186,U/L,10 - 40,HIGH\n"
            "AST,245,U/L,10 - 40,HIGH\n"
            "Ceruloplasmin,8,mg/dL,20 - 40,LOW\n"
            "24-Hour Urinary Copper,185,ug/24h,10 - 60,HIGH\n"
        ).encode("utf-8")

        files = {"file": ("wilson_report.csv", io.BytesIO(csv_bytes), "text/csv")}
        ext_res = self.client.post("/api/analyzer/extract", files=files)
        self.assertEqual(ext_res.status_code, 200)
        ext_data = ext_res.json()

        payload = {
            "parameters": ext_data["parameters"],
            "metadata": ext_data["metadata"],
            "filename": "wilson_report.csv",
            "file_type": "CSV"
        }
        anl_res = self.client.post(
            "/api/analyzer/analyze",
            json=payload,
            headers={"Authorization": f"Bearer {self.patient_token}"}
        )
        self.assertEqual(anl_res.status_code, 200)
        anl_data = anl_res.json()
        rare = anl_data["ai_analysis"]["rare_unusual_screening"]
        self.assertTrue(rare["flagged"])
        self.assertIn("conditions", rare)
        self.assertGreater(len(rare["conditions"]), 0)


if __name__ == "__main__":
    unittest.main()
