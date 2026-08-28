# MEDLENS Modular System Architecture

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MEDLENS UNIFIED HEALTH PLATFORM                      │
│                                                                        │
│   ┌─────────────────────────────────┐ ┌────────────────────────────┐   │
│   │   Digital Pathology & AI/ML     │ │   Hospital Operations      │   │
│   │   Decision Support Module       │ │   Intelligence Module      │   │
│   │  - 5 Trained ML Pipelines       │ │  - 3-Source Ingestion      │   │
│   │  - Rare Disease Screening       │ │  - Deterministic Rules     │   │
│   │  - AI Health Report Analyzer    │ │  - Conflict Explorer       │   │
│   │  - Doctor & Patient Portals     │ │  - Unified Ops Dashboard   │   │
│   └─────────────────────────────────┘ └────────────────────────────┘   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │      FastAPI REST Services      │
                    │  (Port 8000 & Webhook Gateway)  │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │      SQLite Secure Storage      │
                    │   (PBKDF2 Hashed, RBAC, Audited) │
                    └─────────────────────────────────┘
```

---

## Core Backend Modules (`hospital_operations/`)

1. **`ingestion/loader.py`**: Safe reader for the 3 official CSV extracts.
2. **`normalization/standardizer.py`**: Standardizes patient IDs, ISO dates, ward names, and clinical priorities.
3. **`matching/matcher.py`**: Cross-source 3-way matching across HIS, LAB, and BED.
4. **`reconciliation/rules.py` & `engine.py`**: Deterministic resolution engine with 7 documented rules and "Why?" explanation generator.
5. **`metrics/`**: Computes census, bed capacity, lab turnaround, and data quality score.
6. **`alerts/alert_engine.py`**: Rule-based operational alert generator.
7. **`reports/daily_report.py`**: Generates daily briefings in HTML, PDF-ready, and CSV formats.
8. **`ai_summary/ops_summarizer.py`**: Grounded AI executive summaries with deterministic fallback.
9. **`service.py`**: Master singleton orchestrator and caching layer.
