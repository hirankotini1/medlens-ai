# Entity-Relationship (ER) Diagram

The following diagram illustrates the relational schema and cardinality of the **Nexus Pathology** database.

```mermaid
erDiagram
    PATIENTS ||--o{ LAB_REPORTS : "has"
    PATIENTS ||--o{ ML_PREDICTIONS : "associated with"
    LAB_REPORTS ||--o{ ML_PREDICTIONS : "evaluated by"
    USERS {
        int id PK
        string username UK
        string role
        string password_hash
        string created_at
    }

    PATIENTS {
        int id PK
        string patient_id UK "e.g. PAT-1001"
        string name
        int age
        string gender
        string contact
        string email
        string access_pin_hash "PBKDF2-HMAC-SHA256"
        string created_at
    }

    LAB_REPORTS {
        int id PK
        string report_id UK "e.g. REP-2026-001"
        string patient_id FK "References PATIENTS"
        string test_category "anemia, dengue, liver, thyroid"
        string status "Draft / Finalized"
        string lab_technician
        string doctor_remarks
        text report_data "Structured JSON"
        string created_at
        string updated_at
    }

    ML_PREDICTIONS {
        int id PK
        string patient_id FK "References PATIENTS"
        string report_id FK "References LAB_REPORTS"
        string disease
        string prediction "e.g. Anemic, Positive"
        real confidence "0.0 - 1.0"
        string risk_level "High Risk / Normal"
        string model_version "e.g. anemia_pipeline.joblib"
        string model_used "e.g. Logistic Regression"
        text input_snapshot "Structured JSON"
        string disclaimer
        string created_at
    }
```

---

## Relationship Cardinality & Constraints

1. **`patients` $\leftrightarrow$ `lab_reports` (1 : N):**
   * One patient can have zero, one, or multiple laboratory reports over time.
   * Every laboratory report must reference a valid `patient_id` via a foreign key constraint.
2. **`lab_reports` $\leftrightarrow$ `ml_predictions` (1 : N):**
   * One laboratory report can be evaluated multiple times by ML pipelines (e.g., following model updates or re-analysis).
   * Every ML prediction is strictly linked to the originating `report_id` and `patient_id`.
3. **`users` (Independent Entity):**
   * Manages staff authentication and role permissions without direct foreign-key coupling to clinical reports, preserving staff anonymity in patient-facing report views while logging technician names in `lab_reports.lab_technician`.
