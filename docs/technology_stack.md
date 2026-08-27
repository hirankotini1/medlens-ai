# Technology Stack Specification

This document details the software technologies, frameworks, libraries, and protocols utilized across the **Nexus Pathology** platform.

---

## 1. Frontend Technology Stack

* **HTML5:** Semantic markup structure (`<header>`, `<main>`, `<section>`, `<nav>`, `<form>`, `<table>`).
* **Vanilla CSS3:**
  * Modern CSS Custom Properties (Variables) for dark-mode theming.
  * Responsive Layouts via CSS Flexbox and CSS Grid.
  * Backdrop filters (`backdrop-filter: blur()`) for glassmorphism aesthetics.
  * Dedicated Print Media Stylesheet (`@media print`) for formatting physical pathology reports.
  * Zero heavy external CSS frameworks (no Tailwind/Bootstrap overhead).
* **Vanilla JavaScript (ES6+):**
  * Asynchronous HTTP communication via the native `fetch` API.
  * Event-driven client state management for session tokens, role switching, and modal controls.
  * Dynamic DOM construction for structured laboratory parameter tables and ML result cards.
  * HTML5 Drag & Drop API and `FileReader` for microscopy cell image uploads.
* **Typography:** Google Fonts (`Plus Jakarta Sans`).

---

## 2. Backend & Application Stack

* **Language:** Python 3.12 (compatible with Python 3.10+)
* **Web Framework:** **FastAPI 0.115+**
  * Asynchronous RESTful routing and dependency injection.
  * Automatic OpenAPI (Swagger) schema generation at `/docs`.
* **ASGI Web Server:** **Uvicorn 0.34+**
  * High-performance asynchronous server implementation for ASGI applications.
* **Data Validation:** **Pydantic v2.10+**
  * Strict schema validation for incoming clinical metrics and parameter boundary enforcement.
* **Security & Cryptography:**
  * `hashlib` — PBKDF2-HMAC-SHA256 password and PIN hashing (100,000 iterations + 16-byte random salts).
  * `hmac` & `secrets` — Cryptographic signature verification and session token generation (`secrets.compare_digest`).

---

## 3. Database & Persistence Stack

* **Database Management System:** **SQLite 3**
* **Driver:** Python native `sqlite3` module.
* **Configuration:**
  * Foreign key enforcement enabled.
  * Row factory mapping (`sqlite3.Row`) for dictionary conversions.
  * Parameterized SQL queries using `?` placeholders.
  * SQLite Online Backup API (`conn.backup()`) for non-blocking database backup snapshots.

---

## 4. Machine Learning & Computer Vision Stack

* **Machine Learning Library:** **Scikit-Learn 1.6+**
  * Pipeline serialization (`joblib`).
  * Classifiers: `LogisticRegression`, `RandomForestClassifier`, `GradientBoostingClassifier`.
  * Preprocessing: `StandardScaler`, `OneHotEncoder`, `SimpleImputer`.
  * Metrics: `classification_report`, `confusion_matrix`, `cross_val_score`, `roc_auc_score`.
* **Computer Vision & Image Processing:** **OpenCV 4.10+ (`cv2`)**
  * In-memory buffer image decoding (`cv2.imdecode`).
  * Color space conversions (BGR $\to$ HSV, BGR $\to$ LAB).
  * Color histogram extraction and Hu Moments shape descriptors.
* **Numerical & Data Processing:**
  * **Pandas 2.2+** — Dataframe manipulation and feature matrix construction.
  * **NumPy 2.0+** — Multidimensional array operations and image matrix calculations.
  * **SciPy 1.14+** — Statistical moment calculations (skewness, kurtosis).

---

## 5. Testing & Quality Assurance Stack

* **Test Runner:** Python standard library `unittest` and `FastAPI TestClient` (via `starlette` / `httpx`).
* **Test Suites:**
  * `security_audit/security_tests.py` (15 Security & IDOR Scenarios)
  * `test_pathology_system.py` (10 Pathology Workflow Scenarios)
  * `test_api.py` (10 Direct Model Prediction Scenarios)
