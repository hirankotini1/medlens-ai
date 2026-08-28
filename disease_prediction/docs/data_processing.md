# MEDLENS Data Processing & Pipeline Architecture

## Pipeline Workflow

```
[ Raw CSV Extracts: HIS, LAB, BED ]
                │
                ▼
      1. Ingestion Layer
         (Safe loading, raw null/dup tracking)
                │
                ▼
      2. Normalization Layer
         (IDs, Wards, Genders, Priorities, ISO Timestamps)
                │
                ▼
      3. Matching Layer
         (3-Way cross-source matching: Matched, Outpatients, Inpatients)
                │
                ▼
      4. Reconciliation Engine
         (Conflict Detection & Deterministic Rule Application)
                │
                ▼
      5. Metrics & Analytics Engine
         (Census, Ward Capacities, Turnaround Times, Quality Score)
                │
                ▼
      6. Alert & Report Generation
         (Capacity Warnings, STAT Delays, Daily Briefing HTML/PDF/CSV)
                │
                ▼
      7. Unified API & Frontend Presentation
         (Interactive UI, 'Why?' Drilldowns, AI Operations Summary)
```

---

## Performance Optimizations
- **In-Memory Normalization Cache**: Calculations are cached on the singleton service layer. Re-ingestion occurs only when on-demand reconciliation is triggered via `POST /api/operations/reconcile`.
- **Zero Frontend Blocking**: The core dashboard computes and renders instantly (< 50ms) using deterministic mathematical metrics, with non-blocking async generation for optional AI executive summaries.
