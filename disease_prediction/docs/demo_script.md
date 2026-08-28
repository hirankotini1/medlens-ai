# MEDLENS 3-to-5 Minute Judge Demonstration Script

## Step 1: Open MEDLENS Web Application (0:00 - 0:45)
1. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
2. Click **"Hospital Operations"** in the top navigation bar.
3. Show the **4 Core Strategic Leadership Cards**:
   - **Active Inpatients**: 56 patients
   - **Bed Occupancy**: 61.2% (60/98 beds)
   - **Lab Turnaround**: 9.30 hrs
   - **Needs Attention**: 9 active operational alerts & 78.9% Data Quality Score.

---

## Step 2: Show the Three Ingested Data Sources (0:45 - 1:30)
1. Click the **"Data Sources"** sub-tab.
2. Present the 3 official sources:
   - **HIS Admissions & Discharges**: 309 records &bull; Processed.
   - **Lab Order-to-Result**: 607 records &bull; Processed.
   - **Manual Bed Occupancy Sheet**: 130 records &bull; Processed.
3. Highlight that all numbers are computed directly from the supplied extracts without synthetic replacements.

---

## Step 3: Demonstrate "Why Is This Different?" Reconciliation (1:30 - 2:30)
1. Click **"Reconciliation & Conflicts"** sub-tab.
2. Show the catalog of 166 detected discrepancies.
3. Click the **"Why?"** button on any conflict (e.g. `CONF-OCC-2026-07-01-0`).
4. Show the interactive modal displaying:
   - Side-by-side Source A vs Source B
   - Applied Rule: `RULE-REC-03` (Bed Sheet vs HIS Census Reconciliation)
   - Reconciled Final Value
   - Operational Rationale explaining day-care patients and pending discharge paperwork.
5. Click **"How We Resolve"** to show the 7 documented deterministic rules.

---

## Step 4: Highlight Key Operational Bottlenecks (2:30 - 3:30)
1. Click **"Bed Capacity"**: Show the 98-bed hospital capacity, ward-wise breakdown, and 30-day occupancy timeline.
2. Click **"Lab Performance"**: Highlight the major hospital finding:
   - **STAT emergency orders average 9.39 hours** (virtually identical to Routine at 9.17 hours), revealing a critical pre-analytical phlebotomy lag of 95 minutes.
3. Click **"Daily Report"**: Generate the print-ready, high-resolution HTML Executive Briefing and demonstrate CSV export.
4. Click **"AI Summary"**: Show the grounded leadership brief.

---

## Step 5: Seamless Connection to Digital Pathology (3:30 - 4:30)
1. Click **"Home"** &rarr; **"AI Analyzer"**: Upload or analyze a pathology report.
2. Click **"ML Sandbox"**: Demonstrate the 5 trained ML diagnostic models (Anemia, Dengue, Liver, Thyroid, Malaria).
3. Conclude:
   > *"MEDLENS delivers the complete health intelligence platform — combining clinical digital pathology with hospital operations intelligence."*
