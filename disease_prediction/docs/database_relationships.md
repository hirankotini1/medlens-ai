# 🗄️ Supabase Database Architecture & Relationships

## Entity-Relationship Overview

All Staff Operations data is stored centrally in **Supabase PostgreSQL**.

```mermaid
erDiagram
    STAFF_USERS ||--o{ PATIENT_ADMISSIONS : admits
    STAFF_USERS ||--o{ LAB_ORDER_TO_RESULT : completes
    HOSPITAL_BEDS ||--o{ PATIENT_ADMISSIONS : allocates
    REGISTERED_PATIENTS ||--o{ PATIENT_ADMISSIONS : receives
    REGISTERED_PATIENTS ||--o{ LAB_ORDER_TO_RESULT : undergoes

    STAFF_USERS {
        uuid id PK
        string staff_id UK "e.g. REC001, LAB001, WARD001, OPS001"
        string username UK
        string password_hash "SHA-256"
        string role "RECEPTIONIST, LAB_STAFF, WARD_MANAGER, OPERATIONS_MANAGER"
        string department
        string status "ACTIVE"
    }

    HOSPITAL_BEDS {
        uuid id PK
        string bed_id UK "e.g. GEN-A-01, AC-12, PREM-03, ICU-04"
        string ward_name "General Ward A/B, AC Semi-Private, Premium Deluxe, ICU"
        string room_number
        string tier "General, AC, Premium"
        string status "Available, Occupied, Maintenance"
        float daily_rate
    }

    PATIENT_ADMISSIONS {
        uuid id PK
        string patient_id FK
        string patient_name
        string preferred_bed_tier
        string assigned_bed_id FK
        string admitting_department
        string attending_doctor
        boolean insurance_covered
        string insurance_provider
        string status "Admitted, Discharged"
        timestamp admitted_at
        timestamp discharged_at
    }

    LAB_ORDER_TO_RESULT {
        uuid id PK
        string order_id UK "e.g. ORD-1001"
        string patient_id FK
        string test_name
        string ordering_department
        string priority "Routine, STAT"
        string status "Pending, Completed"
        string result_value
        string reference_range
        text technician_notes
        timestamp order_time
        timestamp result_time
    }
```

---

## 🔒 Foreign Key Constraints & Data Invariants

1. **Bed Allocation Invariant**: A bed with status `Occupied` cannot be assigned to another patient until an explicit discharge transaction occurs.
2. **Quota Invariant**: An admission transaction is rejected with `400 BED_QUOTA_FULL` if all beds in the requested category are occupied.
3. **Audit Trail Invariant**: Discharging a patient does not delete the admission record; it updates `status = 'Discharged'` and records `discharged_at`.
