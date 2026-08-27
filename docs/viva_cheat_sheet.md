# Nexus Pathology — One-Page Viva Cheat Sheet

A quick-revision cheat sheet containing all core definitions, model benchmarks, architecture points, and security mechanisms for quick memorization before your viva.

---

## 1. Core Project Definition
* **Name:** Nexus Pathology
* **Definition:** A web-based digital pathology laboratory management system combined with an experimental machine-learning decision-support backend for five disease categories.
* **Core Rule:** **Official laboratory reports are strictly decoupled from ML predictions.** ML analysis never alters official clinical records.

---

## 2. Five Validated Machine Learning Models

| Disease | Algorithm | Inputs | Key Metric | 5-Fold CV |
|---|---|:---:|---|:---:|
| **Anemia (CBC)** | Logistic Regression | 11 Features | Holdout: **100%** | **95.49% $\pm$ 1.64%** |
| **Dengue** | Random Forest | 8 Features | Holdout: **92.93%** (Recall: 93.10%) | **91.30% $\pm$ 2.36%** |
| **Liver Disease** | Gradient Boosting | 10 Features | Holdout: **72.81%** (**Recall: 95.06%**) | **69.30% $\pm$ 2.94%** |
| **Thyroid Profile** | Multinomial Logistic Reg | 5 Features | Holdout: **100%** (3 Classes) | **95.81% $\pm$ 3.09%** |
| **Malaria (Image)** | Gradient Boosting + CV Extractor | 354 Features | Unseen Acc: **94.03%** (**Recall: 97.80%**) | Strict Unseen Test |

* **Malaria Duplicate Audit:** 25 duplicate images were detected via SHA-256 and removed prior to final retraining.
* **Synthetic Data Experiment:** Augmentations (+25%, +50%, +100%) did **not** improve real holdout accuracy (Liver dropped to 66.67%). **Decision: Synthetic data is excluded from production.**

---

## 3. Technology Stack at a Glance
* **Backend:** Python 3.12, FastAPI 0.115+, Uvicorn (ASGI), Pydantic v2.
* **Database:** SQLite 3 (`pathology.db`) with parameterized queries (`?`).
* **Machine Learning:** Scikit-Learn 1.6+, OpenCV 4.10+ (`cv2`), Pandas, NumPy, Joblib.
* **Frontend:** Semantic HTML5, Vanilla CSS3 (Custom properties, `@media print`), ES6+ JavaScript.

---

## 4. Database Schema (4 Tables)
1. `patients`: `patient_id` (UK), `name`, `age`, `gender`, `contact`, `email`, `access_pin_hash` (PBKDF2).
2. `lab_reports`: `report_id` (UK), `patient_id` (FK), `test_category`, `status` (Draft/Finalized), `lab_technician`, `doctor_remarks`, `report_data` (JSON).
3. `ml_predictions`: `patient_id`, `report_id`, `disease`, `prediction`, `confidence`, `risk_level`, `model_version`, `input_snapshot`, `disclaimer`.
4. `users`: `username` (UK), `role` (`admin`/`staff`), `password_hash` (PBKDF2).

---

## 5. Security & Verification Summary
* **Authentication:** Cryptographic PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte random salts) + signed HMAC session tokens.
* **Authorization & IDOR:** Role-Based Access Control (RBAC). Patient A cannot access Patient B's records (HTTP 403 Forbidden).
* **Malaria Upload Security:** 5MB limit, PNG/JPG check, MIME verification, OpenCV in-memory decoding.
* **Automated Tests:** **25 / 25 Scenarios Passing (100% Pass Rate)** in 0.35 seconds.

---

## 6. Key Viva Catchphrases & Ethics
* *"We built five specialized models instead of one monolithic model because biological parameter spaces are heterogeneous."*
* *"Official laboratory reports are immutable medical documents; ML predictions are persisted separately in an audit log."*
* *"In healthcare AI, we prioritize Recall over pure Accuracy to minimize dangerous False Negatives."*
* *"Predictions are experimental decision-support aids for qualified doctors and do not constitute autonomous medical diagnoses."*
