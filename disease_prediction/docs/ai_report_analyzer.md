# Nexus Pathology — AI Health Report Analyzer

The **AI Health Report Analyzer** is an experimental clinical decision-support module integrated into Nexus Pathology. It enables patients, clinicians, and laboratory pathologists to upload complete diagnostic health reports (PDF, CSV, JPG, PNG, TXT), automatically extract and normalize structured biomarker parameters, interactively review and edit values, and receive multi-tier clinical intelligence synthesized from **OpenRouter AI** and the platform's **5 validated production machine learning models**.

---

## 1. Architectural Overview

```
                          ┌────────────────────────┐
                          │   Report File Upload   │
                          │ (PDF, CSV, JPG, PNG)   │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │   Multi-Format Parser  │
                          │   & Biomarker Extractor │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │  Interactive Parameter │
                          │  Review & Editor (UI)  │
                          └───────────┬────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
   ┌──────────────────────────┐              ┌──────────────────────────┐
   │  OpenRouter AI Service   │              │   ML Model Bridge        │
   │  (Clinical Reasoning)    │              │   (Frozen Pipelines)     │
   ├──────────────────────────┤              ├──────────────────────────┤
   │ &bull; Anomaly Detection │              │ &bull; Anemia Pipeline   │
   │ &bull; Pattern Screening │              │ &bull; Dengue Pipeline   │
   │ &bull; Rare Marker Scan  │              │ &bull; Liver Pipeline    │
   │ &bull; Guardrails & PII  │              │ &bull; Thyroid Pipeline  │
   └─────────────┬────────────┘              └─────────────┬────────────┘
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │  Visual Health Summary │
                          │  & PDF/Print Export    │
                          └────────────────────────┘
```

---

## 2. Key Capabilities & Workflow

### Step 1: Multi-Format Ingestion & Extraction
- **Metadata Isolation**: Categorizes `Patient ID`, `Patient Name`, `Age`, `Gender`, `Report ID`, `Date`, and `Referring Doctor` into a dedicated metadata structure. These fields are **strictly excluded** from the biomarker table.
- **PDF Documents**: Ingests PDF reports and extracts tabular text streams using `pypdf`.
- **CSV Data**: Ingests structured comma-separated values, supporting both key-value metadata headers and vertical/horizontal biomarker datasets.
- **Images (PNG, JPG, JPEG)**: Ingests scanned lab reports and blood microscopy images.
- **Plain Text**: Ingests raw clinical notes and copy-pasted diagnostic values.
- **Placeholder Rejection**: Rejects missing-value placeholders (`-1`, `-999`, `null`, `N/A`, `unknown`, `blank`) from entering the biomarker table.

### Step 2: Interactive Parameter Review & Editing
- Extracted parameters are mapped to canonical clinical biomarkers (e.g., Hemoglobin, Platelets, TSH, ALT, Bilirubin) while preserving the `original_name`.
- **Reference Range Preservation**: If the uploaded report contains its own biological reference range, the system extracts and uses it directly.
- **Extraction Confidence**: Scores each biomarker as `HIGH`, `MEDIUM`, or `LOW` (with `⚠️ Review` indicator) to highlight parameters needing verification.
- **Separated Review Screen**:
  - **Part A**: Patient & Report Information metadata panel (editable fields).
  - **Part B**: Laboratory Findings & Clinical Biomarkers table with inline editing, deletion (`[ 🗑️ ]`), and addition (`[ ➕ Add Biomarker ]`).


### Step 3: Multi-Tier Clinical Intelligence
1. **Tier 1 — OpenRouter AI Decision Support**:
   - Anonymizes payload by stripping all PII (patient full names, emails, contact numbers).
   - Generates structured clinical summaries, biomarker explanations, and supportive lifestyle guidance.
   - Enforces clinical non-autonomous guardrails: avoids definitive diagnoses, bans prescription of pharmaceuticals, and uses cautious phrasing (*"Possible condition/pattern"*, *"May warrant further clinical evaluation"*).
2. **Tier 2 — Validated Production ML Models**:
   - Seamlessly executes compatible production pipelines:
     - **Anemia**: Logistic Regression on CBC panel (`anemia_pipeline.joblib`).
     - **Dengue**: Random Forest on hematology panel (`dengue_pipeline.joblib`).
     - **Liver Disease**: Gradient Boosting on LFT panel (`liver_pipeline.joblib`).
     - **Thyroid Disorder**: Multinomial Logistic Regression on thyroid hormone profile (`thyroid_pipeline.joblib`).
   - **Zero Hallucination**: If required biomarkers are absent, the bridge explicitly reports `"Insufficient laboratory data for this model"` without guessing missing features.

### Step 4: Visual Health Summary & Export
- Formats findings in the clean **MedVision AI Teal Clinical Theme**.
- Displays overall attention badge (`NORMAL`, `MODERATE ATTENTION`, `HIGH ATTENTION / ELEVATED RISK`).
- Includes printable visual summary sheet (`[ 📥 Print / Save Visual Summary (PDF) ]`).
- Stores immutable audit records in the SQLite `report_analyses` table with strict patient isolation (IDOR protection).

---

## 3. Configuration & Environment Variables

Store credentials in `disease_prediction/.env` (excluded from git via `.gitignore`):

```env
# OpenRouter API Key for AI Health Report Analyzer
OPENROUTER_API_KEY=your_openrouter_api_key_here

# OpenRouter Model Slug (Default: openrouter/auto)
OPENROUTER_MODEL=openrouter/auto

# App Identification Headers
OPENROUTER_SITE_URL=http://localhost:8000
OPENROUTER_APP_NAME=Nexus Pathology AI Health Report Analyzer
```

---

## 4. API Endpoints Reference

| HTTP Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/analyzer/extract` | Upload report file $\to$ returns extracted parameter list | No |
| `POST` | `/api/analyzer/analyze` | Submit reviewed parameters $\to$ returns AI + ML assessment | Optional (associates with patient if provided) |
| `GET` | `/api/analyzer/history` | Returns analysis history (isolated to current patient or admin) | Yes (Bearer Token) |
| `GET` | `/api/analyzer/{id}` | Returns single analysis record (IDOR protected) | Yes (Bearer Token) |

---

## 5. Automated Verification & Testing

Run the dedicated test suite:
```bash
python -m unittest disease_prediction/test_ai_analyzer.py
```

Run the complete platform regression suite (45/45 tests passing):
```bash
python -m unittest disease_prediction/security_audit/security_tests.py disease_prediction/test_pathology_system.py disease_prediction/test_api.py disease_prediction/test_ai_analyzer.py
```
