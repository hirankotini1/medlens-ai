# Database Design & Schema Specification

The database layer for **Nexus Pathology** is implemented using a SQLite relational database (`pathology.db`). The schema is structured to maintain clinical data integrity, enforce foreign key relationships, and achieve strict decoupling between official laboratory records and probabilistic machine-learning predictions.

---

## 1. Table Definitions

### 1. `patients` Table
Stores patient demographic and identity information.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal database surrogate key |
| `patient_id` | `TEXT` | `UNIQUE NOT NULL` | Unique public identifier (e.g. `PAT-1001`) |
| `name` | `TEXT` | `NOT NULL` | Full patient name |
| `age` | `INTEGER` | `NOT NULL` | Patient age in years |
| `gender` | `TEXT` | `NOT NULL` | Gender (`Male`, `Female`, `Child`, `Other`) |
| `contact` | `TEXT` | `NULLABLE` | Contact telephone number |
| `email` | `TEXT` | `NULLABLE` | Patient email address |
| `access_pin_hash` | `TEXT` | `NOT NULL` | PBKDF2-HMAC-SHA256 hash of patient security PIN |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 creation timestamp |

---

### 2. `lab_reports` Table
Stores authoritative, official laboratory reports authored by clinical staff.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal surrogate key |
| `report_id` | `TEXT` | `UNIQUE NOT NULL` | Unique report identifier (e.g. `REP-2026-001`) |
| `patient_id` | `TEXT` | `NOT NULL`, `FK -> patients(patient_id)` | Associated patient identifier |
| `test_category` | `TEXT` | `NOT NULL` | Test panel (`anemia`, `dengue`, `liver`, `thyroid`) |
| `status` | `TEXT` | `NOT NULL DEFAULT 'Finalized'` | Lifecycle status (`Draft` or `Finalized`) |
| `lab_technician` | `TEXT` | `NULLABLE` | Name and title of reporting technician/pathologist |
| `doctor_remarks` | `TEXT` | `NULLABLE` | Clinical notes, impressions, and recommendations |
| `report_data` | `TEXT` | `NOT NULL` | Structured JSON containing parameter values, units, reference intervals, and abnormality flags |
| `created_at` | `TEXT` | `NOT NULL` | Sampling / creation ISO-8601 timestamp |
| `updated_at` | `TEXT` | `NOT NULL` | Last update ISO-8601 timestamp |

---

### 3. `ml_predictions` Table (Audit Log)
Stores historical records of experimental machine-learning decision support invocations.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal surrogate key |
| `patient_id` | `TEXT` | `NOT NULL`, `FK -> patients(patient_id)` | Associated patient identifier |
| `report_id` | `TEXT` | `NOT NULL`, `FK -> lab_reports(report_id)` | Associated laboratory report identifier |
| `disease` | `TEXT` | `NOT NULL` | Target condition name (e.g. `Anemia`, `Dengue`) |
| `prediction` | `TEXT` | `NOT NULL` | Categorical classification output (e.g. `Anemic`, `Positive`, `Hypothyroid`) |
| `confidence` | `REAL` | `NOT NULL` | Calculated model probability score ($0.0 - 1.0$) |
| `risk_level` | `TEXT` | `NULLABLE` | Risk classification (`High Risk` vs. `Normal / Low Risk`) |
| `model_version` | `TEXT` | `NOT NULL` | Serialized pipeline identifier (e.g. `anemia_pipeline.joblib`) |
| `model_used` | `TEXT` | `NOT NULL` | Name of algorithm (e.g. `Logistic Regression`) |
| `input_snapshot` | `TEXT` | `NOT NULL` | JSON snapshot of input parameters evaluated |
| `disclaimer` | `TEXT` | `NOT NULL` | Full educational/research legal disclaimer text |
| `created_at` | `TEXT` | `NOT NULL` | Execution ISO-8601 timestamp |

---

### 4. `users` Table
Stores laboratory personnel and administrative credentials.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal surrogate key |
| `username` | `TEXT` | `UNIQUE NOT NULL` | Staff login username (e.g. `admin`) |
| `role` | `TEXT` | `NOT NULL DEFAULT 'staff'` | Role (`admin`, `pathologist`, `technician`) |
| `password_hash` | `TEXT` | `NOT NULL` | PBKDF2-HMAC-SHA256 cryptographic password hash |
| `created_at` | `TEXT` | `NOT NULL` | Account creation timestamp |

---

## 2. Rationale for Decoupled ML Predictions

In medical software engineering, conflating official clinical findings with experimental machine-learning predictions introduces severe diagnostic, ethical, and legal risks. Nexus Pathology strictly decouples these tables for the following reasons:
1. **Clinical Immutability:** An official laboratory report is a legal medical document. ML predictions must never overwrite or mutate the recorded biochemical values or doctor remarks.
2. **Independent Auditability:** Separate storage in `ml_predictions` allows retrospective analysis of how models perform over time across various demographic cohorts without altering historical medical records.
3. **Fail-Safe Availability:** If an ML model fails to load or encounter missing features, the official laboratory report remains 100% accessible to the patient and clinician.
