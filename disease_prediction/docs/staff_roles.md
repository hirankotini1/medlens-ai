# 👥 MEDLENS Staff Roles & Access Control

## Role Hierarchy & Permissions

| Role | Access Level | Permitted Operations | Restricted Operations |
| :--- | :--- | :--- | :--- |
| **`RECEPTIONIST`** | Front Desk & Inpatient Intake | Register patients, book doctor appointments, admit inpatients with bed quota checks, calculate & print inpatient billing slips, search registered patients directory | Modifying pathology results, reconfiguring bed topology |
| **`LAB_STAFF`** | Pathology & Diagnostics | View laboratory queue (Routine & STAT), record test values, update normal reference ranges, add clinical notes, compute turnaround times | Inpatient admissions, altering hospital bed inventory |
| **`WARD_MANAGER`** | Floor & Bed Operations | Select from 5 hospital wards, inspect 98 numbered bed matrix, execute sanitization turnover checklists (Green/Yellow/Red), view inpatient ward roster, trigger inpatient billing | Executing hospital-wide data reconciliation overrides |
| **`OPERATIONS_MANAGER`** | Executive Leadership | Macro hospital KPIs, Bed capacity breakdown (General/AC/Premium), Multi-source data reconciliation (HIS, Lab, Bed Sheet), Rule-based conflict explorer, Data quality scorecard (78.9%), AI operations brief | Direct modification of immutable clinical records |

---

## 🔑 Authentication Mechanism

1. **Password Security**: Passwords are saved as SHA-256 hashes in the Supabase PostgreSQL `staff_users` table.
2. **Session Security**: Upon login via `POST /api/operations/auth/login`, the server issues a role-scoped HMAC-signed token.
3. **Role Enforcement**: Protected operational routes use FastAPI's dependency injection (`require_staff_role`) to strictly enforce role separation.
