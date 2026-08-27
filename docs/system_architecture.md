# System Architecture

---

## 1. High-Level Architectural Diagram

```
                              NEXUS PATHOLOGY
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
              ADMIN PORTAL                      PATIENT PORTAL
        (Lab Staff Credentials)           (Patient ID + Security PIN)
                    │                                 │
                    └────────────────┬────────────────┘
                                     │
                              FastAPI Backend
                        (RESTful API & Middleware)
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
             SQLite Database                       ML Layer
             (`pathology.db`)                (5 Validated Pipelines)
                    │                                 │
          ┌─────────┴─────────┐       ┌───────┬───────┼───────┬───────┐
          │ patients          │       │       │       │       │       │
          │ lab_reports       │    Anemia  Dengue   Liver  Thyroid Malaria
          │ ml_predictions    │     Model   Model   Model   Model   Model
          │ users             │       │       │       │       │       │
          └───────────────────┘       └───────┴───────┼───────┴───────┘
                                                      │
                                                      ▼
                                           Experimental ML Analysis
                                           (Confidence, Risk & Disclaimer)
```

---

## 2. Architectural Component Breakdown

### A. Presentation Layer (Frontend Client)
* **Single-Page Application (SPA) Architecture:** Lightweight, responsive vanilla JavaScript client communicating asynchronously via JSON HTTP requests.
* **Role-Based Navigation:** Renders role-specific dashboards based on active authentication state (Admin vs. Patient vs. Public).
* **Decoupled Render Cards:** Ensures the official laboratory document and the experimental ML decision-support output are displayed in completely distinct, independent card containers.

### B. Application Layer (FastAPI Backend)
* **API Gateway & Routing:** Exposes structured endpoints grouped by functionality:
  * `/api/auth/*` — Administrator and patient login & token generation.
  * `/api/patients` — Patient registration and listing.
  * `/api/reports/*` — Laboratory report authoring, retrieval, and updates.
  * `/api/reports/{id}/analyze-ml` — Orchestrates ML pipeline invocation from stored report data.
  * `/predict/*` — Standalone direct prediction endpoints for exploratory testing.
* **Authentication & Authorization Dependency Injection:** Intercepts incoming requests, verifies HMAC session signatures, validates role permissions, and rejects unauthorized or cross-patient IDOR queries.
* **Request Validation:** Employs Pydantic schemas to validate numerical boundaries, non-empty fields, and physiological data types before execution.

### C. Machine Learning Engine
* **Serialized Scikit-Learn Pipelines:** Pre-trained, validated models loaded into memory via `joblib`.
* **Dynamic Pipeline Routing:** Maps test categories (`anemia`, `dengue`, `liver`, `thyroid`, `malaria`) to their specific inference pipelines.
* **Image Processing Subsystem:** Decodes raw binary image buffers into OpenCV color arrays, extracts a 354-dimensional feature vector, and passes the vector to the Malaria Gradient Boosting classifier.

### D. Data Persistence Layer (SQLite Database)
* **Relational Tables:** Stores patients, official laboratory reports, users, and audit logs.
* **Immutable Audit Trail:** `ml_predictions` records every execution of decision support with the input snapshot, model version, calculated confidence, and timestamp.
* **Decoupling Enforcement:** Modifying or running ML analysis never updates the contents of `lab_reports`.
