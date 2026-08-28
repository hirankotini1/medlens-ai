# 🏥 MEDLENS Staff Operations Guide

## Overview

The **MEDLENS Staff Operations Command Center** is a cloud-synchronized Hospital ERP and Multi-Source Intelligence system integrated with **Supabase PostgreSQL**.

It provides dedicated, streamlined operational interfaces for four clinical staff roles:
1. **Receptionist** (Intake, Registration, Inpatient Admissions, Quota Check, Billing)
2. **Lab Staff** (Pathology Orders, TAT Analytics, Result Validation)
3. **Ward Manager** (Floor In-Charge, 98 Numbered Bed Turnover, Inpatient Roster)
4. **Operations Manager** (Executive Overview, Multi-Source Reconciliation, Conflict Engine, Data Quality Scorecard)

---

## 🔒 Protected Features Architecture

MEDLENS strictly isolates Hospital Operations without altering or regressing the 5 Core Clinical Modules:
1. **Patient Login & Portal** (`/api/patient/*`)
2. **Doctor Login & Portal** (`/api/admin/*`)
3. **AI Report Analyzer** (`/api/predict/*`, `/api/report/analyze`)
4. **Symptoms AI Guidance** (`/api/symptoms/*`, `/api/issues/*`)
5. **Machine Learning Sandbox** (`/api/sandbox/*`)

All staff endpoints are namespaced cleanly under `/api/operations/*`.

---

## 🚀 Live Operational Features

- **Single Source of Truth**: All operations (staff authentication, patient intake, bed allocation, lab order completion) query and commit transactions directly to Supabase PostgreSQL.
- **Bed Quota Enforcement**: Automatic validation prevents overbooking. When available beds reach 0, the system immediately locks admissions and displays `🔴 BED QUOTA FULL`.
- **Atomic State Transitions**:
  - Admitting a patient marks the selected bed as `Occupied` in Supabase.
  - Discharging an inpatient marks the bed as `Available` and updates the inpatient census.
  - Lab technicians record results and validation notes with real-time turnaround time (TAT) computation.
