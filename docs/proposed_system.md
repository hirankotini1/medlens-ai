# Proposed System Specification

The **Nexus Pathology** platform is engineered to modernize pathology laboratory management while providing a safe, strictly controlled environment for experimental machine-learning decision support.

---

## 1. System Architecture Overview

The proposed system follows a decoupled, three-tier architecture:
1. **Presentation Layer (Frontend):** Modern, responsive HTML5/CSS3/JavaScript single-page interface with separate views for Landing/About, Patient Dashboard, Administrative Laboratory Operations, and Direct ML Sandbox.
2. **Application & API Layer (Backend):** FastAPI RESTful API server implementing endpoint routing, request validation, authentication, authorization middleware, and machine learning inference coordination.
3. **Persistence & Storage Layer (Database & Models):** SQLite relational database (`pathology.db`) managing relational records, paired with frozen serialized Scikit-Learn pipelines (`models/`).

---

## 2. Core Functional Modules

### A. Patient Portal & Identity Verification
* **Authentication:** Patients authenticate using their unique `patient_id` and a hashed `access_pin`.
* **Personalized Dashboard:** Displays demographic overview, list of personal laboratory reports, report statuses (`Draft` / `Finalized`), and previous decision-support summaries.
* **IDOR Defense:** Patient tokens are cryptographically signed with HMAC-SHA256 and verified on every request. Attempting to query another patient's data results in an immediate `403 Forbidden` response.

### B. Administrative & Laboratory Staff Portal
* **Staff Authentication:** Restricted to authorized staff via cryptographic PBKDF2-HMAC-SHA256 password verification.
* **Patient Registration:** Streamlined entry for patient demographics with automatic PIN generation.
* **Smart Laboratory Report Creation:** Five pre-configured clinical templates (Anemia CBC, Dengue Hematology, Liver LFT, Thyroid Profile, Malaria Microscopy). Only relevant fields are displayed, complete with inline biological reference intervals and unit indicators.
* **Report Lifecycle:** Reports can be saved as `Draft` (editable) or `Finalized` (locked official record).

### C. Decoupled Experimental ML Decision Support
* **On-Demand Execution:** Lab staff or patients can trigger ML evaluation on a stored report.
* **Parameter Validation:** Ensures all required clinical features are present in the report before passing them to the pipeline; incomplete reports return a descriptive `422 Unprocessable Entity` error.
* **Separate Display & Disclaimer:** Rendered in an independent card with calculated confidence, risk classification, model provenance, and mandatory educational/research disclaimers. Official lab values remain completely unmodified.

### D. Direct ML Sandbox
* Interactive playground allowing clinicians and researchers to test model predictions directly against arbitrary parameter inputs or uploaded blood smear microscopy images.
