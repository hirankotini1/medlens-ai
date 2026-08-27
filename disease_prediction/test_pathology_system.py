import os
import sys
import unittest
import numpy as np
import cv2
from fastapi.testclient import TestClient

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from disease_prediction.api.main import app, generate_signed_token
from disease_prediction.api import database as db

client = TestClient(app)

class TestPathologySystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        db.init_db()
        db.reset_to_clean_seed()
        cls.admin_token = generate_signed_token({"sub": "admin", "role": "admin"})
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.patient_a_token = generate_signed_token({"sub": "PAT-1001", "role": "patient", "patient_id": "PAT-1001"})
        cls.patient_a_headers = {"Authorization": f"Bearer {cls.patient_a_token}"}


    @classmethod
    def tearDownClass(cls):
        db.reset_to_clean_seed()


    def test_01_health_check(self):
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        for model_key, is_avail in data["models_available"].items():
            self.assertTrue(is_avail, f"Model {model_key} should be available.")

    def test_02_patient_management(self):
        new_patient = {
            "name": "Vikram Sethi",
            "age": 52,
            "gender": "Male",
            "contact": "+91-9988776655",
            "email": "vikram.sethi@example.com"
        }
        res = client.post("/api/patients", json=new_patient, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        p_data = res.json()
        self.assertIn("patient_id", p_data)
        self.assertEqual(p_data["name"], "Vikram Sethi")

        res_list = client.get("/api/patients", headers=self.admin_headers)
        self.assertEqual(res_list.status_code, 200)
        patients = res_list.json()
        self.assertTrue(len(patients) >= 5)

    def test_03_report_creation_and_retrieval(self):
        report_payload = {
            "patient_id": "PAT-1001",
            "test_category": "anemia",
            "status": "Finalized",
            "lab_technician": "Dr. A. K. Mehta",
            "doctor_remarks": "Test CBC report for automated test suite",
            "report_data": {
                "Age": 28,
                "Sex": "Female",
                "HGB": 8.2,
                "RBC": 3.6,
                "PCV": 25.0,
                "MCV": 68.0,
                "MCH": 20.0,
                "MCHC": 28.0,
                "RDW": 19.0,
                "TLC": 7.0,
                "PLT /mm3": 180.0
            }
        }
        res = client.post("/api/reports", json=report_payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        rep = res.json()
        self.assertIn("report_id", rep)
        self.assertEqual(rep["patient_id"], "PAT-1001")

        res_get = client.get(f"/api/reports/{rep['report_id']}", headers=self.patient_a_headers)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["report_id"], rep["report_id"])

    def test_04_report_linked_anemia_ml_analysis(self):
        res = client.post("/api/reports/REP-2026-001/analyze-ml", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["disease"], "Anemia")
        self.assertEqual(data["prediction"], "Anemic")
        self.assertTrue(data["confidence"] > 0.90)
        self.assertEqual(data["model_version"], "anemia_pipeline.joblib")
        self.assertIn("disclaimer", data)

    def test_05_report_linked_dengue_ml_analysis(self):
        res = client.post("/api/reports/REP-2026-002/analyze-ml", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["disease"], "Dengue")
        self.assertEqual(data["prediction"], "Positive")
        self.assertTrue(data["confidence"] > 0.85)

    def test_06_report_linked_liver_ml_analysis(self):
        res = client.post("/api/reports/REP-2026-003/analyze-ml", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["disease"], "Liver Disease")
        self.assertEqual(data["prediction"], "Liver Disease")

    def test_07_report_linked_thyroid_ml_analysis(self):
        res = client.post("/api/reports/REP-2026-004/analyze-ml", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["disease"], "Thyroid Disorder")
        self.assertEqual(data["prediction"], "Hypothyroid")

    def test_08_malaria_microscopy_image_prediction(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        cv2.circle(img, (50, 50), 12, (150, 40, 80), -1)
        cv2.circle(img, (48, 48), 5, (220, 20, 40), -1)
        
        _, img_bytes = cv2.imencode('.png', img)
        files = {"file": ("cell_smear.png", img_bytes.tobytes(), "image/png")}
        
        res = client.post("/predict/malaria", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["disease"], "Malaria")
        self.assertIn("prediction", data)
        self.assertIn("confidence", data)

    def test_09_missing_value_handling(self):
        incomplete_report = {
            "patient_id": "PAT-1002",
            "test_category": "dengue",
            "status": "Finalized",
            "report_data": {
                "age": 43
            }
        }
        res_rep = client.post("/api/reports", json=incomplete_report, headers=self.admin_headers)
        rep_id = res_rep.json()["report_id"]

        res_ml = client.post(f"/api/reports/{rep_id}/analyze-ml", headers=self.admin_headers)
        self.assertEqual(res_ml.status_code, 422)
        err_msg = res_ml.json()["detail"]
        self.assertIn("missing", err_msg.lower())
        self.assertIn("hemoglobin_g_dl", err_msg)

    def test_10_patient_isolation_and_predictions_history(self):
        res = client.get("/api/reports?patient_id=PAT-1003", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        reports = res.json()
        for r in reports:
            self.assertEqual(r["patient_id"], "PAT-1003")

        res_hist = client.get("/api/reports/REP-2026-001/predictions", headers=self.patient_a_headers)
        self.assertEqual(res_hist.status_code, 200)
        preds = res_hist.json()
        self.assertTrue(len(preds) >= 1)
        self.assertEqual(preds[0]["disease"], "Anemia")

if __name__ == "__main__":
    unittest.main()
