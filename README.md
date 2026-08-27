# Nexus Pathology — Digital Pathology Platform & Clinical ML Decision Support

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.6+-F7931E.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/Tests-25%2F25%20Passing-success.svg)](#running-automated-tests)
[![Security](https://img.shields.io/badge/Security-PBKDF2%20%7C%20RBAC%20%7C%20IDOR--Protected-brightgreen.svg)](#cybersecurity-controls)

**Nexus Pathology** is a web-based digital pathology laboratory management platform combined with an experimental machine-learning decision-support backend serving five validated diagnostic models: **Complete Blood Count (Anemia)**, **Dengue Hematology**, **Liver Function Test (LFT)**, **Thyroid Profile**, and **Malaria Blood Smear Cell Microscopy**.

---

## Key Features

1. **Patient Portal:** Authenticated, privacy-preserving portal where patients can access their official laboratory reports, view biological reference intervals and clinical flags (Normal, Low, High, Critical), read doctor remarks, and view separate ML analysis summaries.
2. **Administrative & Laboratory Staff Portal:** Operations management for registering patients, authoring structured clinical reports with dynamic parameter panels, managing report lifecycles (Draft vs. Finalized), and triggering on-demand ML decision support.
3. **Strict Report Decoupling:** Official medical findings (`lab_reports`) remain immutable and uncorrupted by ML inferences. All generated predictions are recorded separately in an independent audit log (`ml_predictions`).
4. **Five Validated ML Pipelines:** Pre-trained and serialized Scikit-Learn models with zero data leakage, evaluated via 5-fold cross-validation.
5. **Direct ML Sandbox:** Exploratory testing playground with realistic clinical presets and a secure drag-and-drop microscopy image upload interface for Malaria detection.
6. **Cybersecurity & Privacy Controls:** Cryptographic PBKDF2-HMAC-SHA256 password and PIN hashing, HMAC-signed session tokens, Role-Based Access Control (RBAC), and strict defenses against Insecure Direct Object References (IDOR).
7. **Print & PDF Layout:** Native `@media print` styling that formats the official findings into a physical laboratory report sheet.

---

## Validated Production Models (`disease_prediction/models/`)

| Disease / Panel | Algorithm | Input Dimensions | Holdout Accuracy | 5-Fold Cross-Validation | Primary Metric |
|---|---|:---:|:---:|:---:|---|
| **Anemia (CBC)** | Logistic Regression | 11 Features | **100.00%** | **95.49% $\pm$ 1.64%** | F1: 100% |
| **Dengue** | Random Forest Classifier | 8 Features | **92.93%** | **91.30% $\pm$ 2.36%** | Recall: 93.10% |
| **Liver Disease** | Gradient Boosting | 10 Features | **72.81%** | **69.30% $\pm$ 2.94%** | **Recall: 95.06%** |
| **Thyroid Profile** | Multinomial Logistic Regression | 5 Features | **100.00%** | **95.81% $\pm$ 3.09%** | Multi-class F1: 100% |
| **Malaria (Image)** | Gradient Boosting + CV Extractor | 354 Features | **94.03%** | *Strict Unseen Holdout* | **Recall: 97.80%** |

*(Note: Synthetic data experiments demonstrated that baseline real-data models outperformed or matched synthetic augmentations. Consequently, synthetic data is strictly excluded from production).*

---

## Quick Start & Installation

### 1. Prerequisites
* Python 3.10, 3.11, or 3.12 installed on your system.

### 2. Install Dependencies
```bash
pip install -r disease_prediction/requirements.txt
```

### 3. Start the Web Application
```bash
python -m uvicorn disease_prediction.api.main:app --host 127.0.0.1 --port 8000
```

### 4. Open in Web Browser
Navigate to **`http://127.0.0.1:8000/`** to access the interactive web application.
Interactive OpenAPI (Swagger) API documentation is available at **`http://127.0.0.1:8000/docs`**.

---

## Demonstration Credentials

> **IMPORTANT:** The following credentials are provided **FOR LOCAL DEMONSTRATION ONLY — DO NOT USE THESE CREDENTIALS IN A PRODUCTION DEPLOYMENT.**

### 1. Administrative / Laboratory Staff
* **Username:** `admin`
* **Password:** `admin123`

### 2. Demo Patient Accounts
* **Patient 1 (Anemia CBC Panel):** Patient ID: `PAT-1001` | Security PIN: `PIN-1001`
* **Patient 2 (Dengue Hematology):** Patient ID: `PAT-1002` | Security PIN: `PIN-1002`
* **Patient 3 (Liver LFT Panel):** Patient ID: `PAT-1003` | Security PIN: `PIN-1003`
* **Patient 4 (Thyroid Hormone Profile):** Patient ID: `PAT-1004` | Security PIN: `PIN-1004`

---

## Running Automated Tests

Run the consolidated test suite covering security, IDOR, integration, and direct API endpoints:

```bash
python -m unittest disease_prediction/security_audit/security_tests.py disease_prediction/test_pathology_system.py disease_prediction/test_api.py
```

**Expected Result:**
```
Ran 25 tests in 0.35s
OK
```

---

## Project Documentation (`docs/`)

Comprehensive documentation prepared for college project reports, viva defense, and technical evaluation:

* [`docs/project_abstract.md`](docs/project_abstract.md) — Academic abstract
* [`docs/problem_statement.md`](docs/problem_statement.md) — Problem statement
* [`docs/objectives.md`](docs/objectives.md) — Project objectives
* [`docs/existing_system.md`](docs/existing_system.md) — Existing vs proposed system comparison
* [`docs/proposed_system.md`](docs/proposed_system.md) — Proposed system functional specifications
* [`docs/system_requirements.md`](docs/system_requirements.md) — Hardware and software requirements
* [`docs/system_architecture.md`](docs/system_architecture.md) — Architecture diagrams and layer breakdown
* [`docs/database_design.md`](docs/database_design.md) — Table definitions, constraints, and data dictionaries
* [`docs/er_diagram.md`](docs/er_diagram.md) — Entity-Relationship (ER) Mermaid diagram
* [`docs/ml_methodology.md`](docs/ml_methodology.md) — Machine learning workflow and leakage audit protocols
* [`docs/dataset_description.md`](docs/dataset_description.md) — Features, units, and clinical parameters
* [`docs/model_results.md`](docs/model_results.md) — Holdout, cross-validation, precision, recall, and F1 benchmarks
* [`docs/synthetic_data_experiment.md`](docs/synthetic_data_experiment.md) — Controlled synthetic data experiment analysis
* [`docs/security.md`](docs/security.md) — Cryptographic, RBAC, IDOR, and upload security controls
* [`docs/testing.md`](docs/testing.md) — Verification suite scenario breakdown
* [`docs/limitations.md`](docs/limitations.md) — Academic, dataset, and clinical limitations
* [`docs/future_scope.md`](docs/future_scope.md) — Explainable AI (SHAP), HL7/FHIR, and enterprise scaling
* [`docs/conclusion.md`](docs/conclusion.md) — Project summary and conclusions
* [`docs/viva_questions.md`](docs/viva_questions.md) — 45 college viva questions with answers
* [`docs/presentation_outline.md`](docs/presentation_outline.md) — 15-slide presentation slide outline
* [`docs/live_demo_script.md`](docs/live_demo_script.md) — Step-by-step live demonstration script
* [`docs/technology_stack.md`](docs/technology_stack.md) — Comprehensive technology stack specifications

---

## Ethical & Medical Disclaimer

> **IMPORTANT NOTICE:** This application and its associated machine-learning models are developed for **educational, academic, and clinical decision-support research purposes only**. The system does **not** provide confirmed medical diagnoses, is not certified as a medical device, and must not replace evaluation by licensed physicians, pathologists, or certified healthcare professionals.
