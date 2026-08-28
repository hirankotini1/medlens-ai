# MEDLENS Deterministic Reconciliation Rules Catalog

MEDLENS applies 7 explicit, deterministic, and auditable rules to resolve cross-source disagreements. Zero rows are silently dropped or deleted.

---

### RULE-REC-01: Patient Identifier Normalization & Outpatient Classification
- **Category**: Patient Identity
- **Primary Source**: HIS Admissions & Discharges
- **Secondary Source**: Lab Order-to-Result
- **Problem**: Patient IDs in HIS are prefixed (`MCH-0001001`) while Lab uses bare numeric IDs (`1023`) or `7xxx` series.
- **Rationale**: Lab orders with `7xxx` series represent Outpatients/Walk-ins who receive diagnostic services without inpatient bed admission.
- **Action**: Canonicalize all patient IDs to `MCH-XXXXXXX`. Categorize `7xxx` series as Outpatient Diagnostic Services without dropping them.

---

### RULE-REC-02: HIS Duplicate Admission Record Resolution
- **Category**: Admissions & Census
- **Primary Source**: HIS Admissions & Discharges
- **Problem**: Detects duplicate admission rows for the same patient in the HIS extract (`MCH-0001007`, `MCH-0001071`, `MCH-0001152`, `MCH-0001168`, `MCH-0001192`, `MCH-0001278`).
- **Rationale**: Network re-transmission or double entry in HIS causes duplicated rows at end of file.
- **Action**: Retain the initial verified admission record for active inpatient census calculation. Record secondary duplicate rows in Conflict Register as `DUPLICATE_HIS_RECORD` with original indices preserved.

---

### RULE-REC-03: Manual Bed Sheet vs HIS Inpatient Census Reconciliation
- **Category**: Bed Management
- **Primary Source**: Manual Bed Occupancy Sheet
- **Secondary Source**: HIS Admissions & Discharges
- **Problem**: Reconciles discrepancies between the manual nursing bed log and calculated HIS active patient occupancy for the same ward and date.
- **Rationale**: Manual bed counts frequently include day-care procedures, temporary hallway overflow, or pending discharge paperwork not yet updated in the HIS ledger.
- **Action**:
  1. If Bed Remarks cite *"day-care patient"*, inpatient bed occupancy = `Bed Occupied - Daycare count`.
  2. If Bed Remarks cite *"pending paperwork"*, physical occupancy is preserved from Bed Sheet while administrative status reflects HIS.
  3. If Bed Remarks cite *"approx - system was down"*, HIS timestamped admissions are prioritized.

---

### RULE-REC-04: Missing Bed Sheet Entry Imputation & Auditing
- **Category**: Bed Management
- **Primary Source**: HIS Admissions & Discharges
- **Secondary Source**: Manual Bed Occupancy Sheet
- **Problem**: Identifies days entirely missing from the manual bed occupancy sheet (July 9, 12, 19, 27, 31).
- **Rationale**: Nursing staff omitted manual logging on 5 dates during July 2026.
- **Action**: Impute bed occupancy for missing dates using active HIS patient census filtered by ward capacity. Explicitly flag the record as `IMPUTED_FROM_HIS_DUE_TO_MISSING_BED_SHEET` in the audit trail.

---

### RULE-REC-05: Missing Available Bed Math Computation
- **Category**: Data Quality
- **Primary Source**: Manual Bed Occupancy Sheet
- **Problem**: Handles blank/NaN entries in the 'Available' column of the manual bed sheet (8 occurrences).
- **Rationale**: Nursing staff entered Total Beds and Occupied but omitted calculating Available beds.
- **Action**: Compute `Available Beds = max(0, Total Beds - Occupied)` deterministically, tagging the field as `CALCULATED_MISSING_FIELD`.

---

### RULE-REC-06: Laboratory Turnaround & STAT Delay Classification
- **Category**: Laboratory Operations
- **Primary Source**: Lab Order-to-Result
- **Problem**: Measures exact order-to-collection and collection-to-result durations across STAT, URGENT, and ROUTINE test tiers.
- **Rationale**: Highlights systemic diagnostic bottlenecks where critical emergency orders experience routine-level delays.
- **Action**: Calculate durations from raw timestamps. Flag STAT orders exceeding 2 hours and URGENT orders exceeding 4 hours as Operational Delays.

---

### RULE-REC-07: Canonical Ward Taxonomy Standardization
- **Category**: Facility & Taxonomy
- **Primary Source**: HIS & Bed Sources
- **Problem**: Maps non-standard ward strings (`I.C.U.`, `MICU `, `Gen Ward A`, `Paediatrics `) to the hospital's 5 official wards.
- **Rationale**: Disparate spelling and trailing spaces cause fragmented reporting.
- **Action**: Map all ward entities to canonical names: Intensive Care Unit (ICU), Medical ICU (MICU), General Ward A, General Ward B, Paediatrics.
