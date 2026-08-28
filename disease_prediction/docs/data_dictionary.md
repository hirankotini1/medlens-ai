# MEDLENS Official Hackathon Data Dictionary

This data dictionary is created strictly from the actual supplied files in `medicover data/` covering **01-Jul-2026 to 30-Jul-2026**.

---

## 1. HIS Admissions & Discharges (`01_his_admissions_discharges.csv`)
- **Total Records**: 309 rows
- **Columns (7)**:
  - `patient_id` *(string)*: Inpatient identifier with prefix `MCH-0001001` through `MCH-0001300`. (303 unique IDs, 6 secondary duplicates at rows 303–308).
  - `admission_datetime` *(string)*: ISO timestamp format `%Y-%m-%d %H:%M:%S`. Range: 2026-06-24 to 2026-07-30.
  - `discharge_datetime` *(string, nullable)*: ISO timestamp format `%Y-%m-%d %H:%M:%S`. Null in 56 rows (denoting active, undischarged patients).
  - `ward` *(string)*: Ward names with casing and trailing spaces (`Gen Ward B `, `MICU `, `GEN WARD A`, `PAEDIATRICS `).
  - `admitting_department` *(string)*: Clinical specialty (`General Medicine`, `Orthopaedics`, `Cardiology`, `Paediatrics`, `Pulmonology`, `Emergency`).
  - `age` *(integer)*: Patient age (Range: 1 to 94).
  - `gender` *(string)*: Mixed representations (`Female`, `m`, `M`, `Male`, `F`, `f`).

---

## 2. Laboratory Order-to-Result Turnaround (`02_lab_order_to_result.csv`)
- **Total Records**: 607 rows
- **Columns (8)**:
  - `order_id` *(string)*: Unique lab order number (`LAB500001` to `LAB500607`).
  - `patient_id` *(integer)*: Bare numeric patient ID (`1023` maps to `MCH-0001023`; `7xxx` series represent 34 outpatient walk-ins).
  - `test_name` *(string)*: Diagnostic panel (`KFT`, `Troponin I`, `Serum Electrolytes`, `CBC`, `Blood Culture`, `CRP`, `LFT`, `ABG`).
  - `ordered_at` *(string)*: Order placement timestamp (`DD/MM/YYYY HH:MM`).
  - `collected_at` *(string)*: Sample phlebotomy collection timestamp (`DD/MM/YYYY HH:MM`).
  - `resulted_at` *(string, nullable)*: Analyzer result timestamp (`DD/MM/YYYY HH:MM`). Null in 28 rows (active pending queue).
  - `priority` *(string)*: Priority level with mixed casing (`Stat`, `STAT`, `URGENT`, `Routine`, `routine`).
  - `department` *(string)*: Ordering department.

---

## 3. Manual Bed Occupancy Sheet (`03_bed_occupancy_manual.csv`)
- **Total Records**: 130 rows (26 days $\times$ 5 wards)
- **Columns (6)**:
  - `Date` *(string)*: Format `DD-Mon-YY` (e.g. `01-Jul-26` to `30-Jul-26`). Note: 5 dates omitted (July 9, 12, 19, 27, 31).
  - `Ward` *(string)*: `I.C.U.`, `Medical ICU`, `General Ward - A`, `General Ward B`, `Pediatrics`.
  - `Total Beds` *(integer)*: Capacity per ward (ICU: 12, MICU: 10, Gen Ward A: 30, Gen Ward B: 30, Pediatrics: 16. Total: 98 beds).
  - `Occupied` *(integer)*: Manually counted bed occupancy for shift.
  - `Available` *(float, nullable)*: Null in 8 rows (computed as `Total - Occupied`).
  - `Remarks` *(string, nullable)*: Contextual notes (`"approx - system was down"`, `"includes 1 day-care patient"`, `"2 discharges pending paperwork"`, `"night shift handover count"`, `"verified with nursing station"`).
