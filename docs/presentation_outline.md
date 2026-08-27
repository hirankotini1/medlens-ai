# College Project Presentation Slide Outline (15 Slides)

A 15-slide presentation structure designed for university project reviews, viva defenses, and technical symposiums.

---

### Slide 1: Title Slide
* **Title:** Nexus Pathology
* **Subtitle:** Digital Pathology Laboratory Management Platform with Experimental Machine-Learning Decision Support
* **Presenter:** [Student Name / Roll Number]
* **Department:** Department of Computer Science & Engineering / Information Technology
* **Institution:** [College / University Name]
* **Visual / Graphic:** Nexus Pathology Logo with subtle molecular & computational graphics.

---

### Slide 2: Problem Statement
* **Key Points:**
  * Fragmented paper-based laboratory reporting leads to lost or delayed medical records.
  * Inconvenient and insecure patient access to private diagnostic findings.
  * Clinical laboratory metrics are rarely structured for longitudinal analysis.
  * Disconnect between traditional reporting and modern computational decision-support tools.
  * Security risks: weak access controls, unprotected medical data, and lack of auditability.
* **Visual / Graphic:** Split graphic: Physical paper disarray vs. Clean digital cloud infrastructure.

---

### Slide 3: Project Objectives
* **Key Points:**
  * Build a digital pathology management platform for staff and patients.
  * Provide authenticated, IDOR-protected patient access to laboratory findings.
  * Strictly decouple official clinical reports from probabilistic ML predictions.
  * Train and validate five specialized ML pipelines (Anemia, Dengue, Liver, Thyroid, Malaria).
  * Conduct a controlled synthetic data experiment to evaluate augmentation utility.
  * Implement robust security controls (PBKDF2 hashing, signed tokens, RBAC, input validation).
* **Visual / Graphic:** Icon checklist mapping to core project deliverables.

---

### Slide 4: Existing System vs. Proposed System
* **Key Points:**
  * **Existing System:** Physical records, unauthenticated URLs, casual edits without audit trails, zero integrated computational assistance.
  * **Proposed System (Nexus Pathology):** Centralized relational database, cryptographic authentication, structured reference intervals, decoupled ML decision support, and immutable prediction audit logs.
  * **Core Advantage:** Balances laboratory workflow digitalization with responsible, transparent AI.
* **Visual / Graphic:** Side-by-side comparison table.

---

### Slide 5: System Architecture
* **Key Points:**
  * Three-tier architecture: Presentation Layer (SPA), API Application Layer (FastAPI), Persistence Layer (SQLite + Serialized Pipelines).
  * Role-Based Access Control enforcing distinct views for Admin Staff vs. Patients.
  * On-demand inference coordination between stored clinical metrics and ML models.
  * Independent persistence paths for official laboratory records and ML audit logs.
* **Visual / Graphic:** Architecture Block Diagram from `docs/system_architecture.md`.

---

### Slide 6: Technology Stack
* **Key Points:**
  * **Backend:** Python 3.12, FastAPI 0.115+, Uvicorn (ASGI).
  * **Database:** SQLite 3 with parameterized queries and online backup API.
  * **Machine Learning & Image Processing:** Scikit-Learn 1.6+, OpenCV 4.10+, Pandas, NumPy, Joblib.
  * **Security & Auth:** PBKDF2-HMAC-SHA256, HMAC Bearer tokens, Pydantic v2 schemas.
  * **Frontend:** Modern Semantic HTML5, Vanilla CSS3 (CSS Variables, Flexbox, Grid, `@media print`), ES6+ JavaScript.
* **Visual / Graphic:** Technology logo grid.

---

### Slide 7: Database Design & Decoupled Schema
* **Key Points:**
  * Four relational tables: `patients`, `lab_reports`, `ml_predictions`, and `users`.
  * `lab_reports` stores official parameters, units, reference ranges, flags, and remarks.
  * `ml_predictions` stores an immutable audit record of every generated prediction with input snapshots.
  * **Decoupling Guarantee:** ML analysis never modifies or overwrites official laboratory data.
* **Visual / Graphic:** Database Entity-Relationship (ER) Diagram.

---

### Slide 8: Machine Learning Methodology & Leakage Prevention
* **Key Points:**
  * Five specialized pipelines tailored to specific clinical investigations.
  * Zero-leakage protocols: Transformers fitted strictly within training sets.
  * 5-Fold Cross-Validation with in-fold preprocessing.
  * Cryptographic SHA-256 duplicate image detection (25 duplicate images removed from Malaria set).
  * Pydantic physiological range validation before pipeline ingestion.
* **Visual / Graphic:** ML lifecycle workflow flowchart.

---

### Slide 9: Five Disease-Specific Models
* **Key Points:**
  * **Anemia:** Logistic Regression (11 CBC parameters).
  * **Dengue:** Random Forest Classifier (8 hematology parameters).
  * **Liver Disease:** Gradient Boosting Classifier (10 hepatic enzymes & proteins).
  * **Thyroid Profile:** Multinomial Logistic Regression (5 hormone metrics, 3 classes).
  * **Malaria:** Gradient Boosting + 354-D Color/Moments/Texture Feature Extractor.
* **Visual / Graphic:** Grid of 5 disease cards with icons and key parameters.

---

### Slide 10: Model Evaluation & Benchmark Results
* **Key Points:**
  * Anemia: 100% Holdout, 95.49% $\pm$ 1.64% 5-Fold CV.
  * Dengue: 92.93% Holdout, 91.30% $\pm$ 2.36% 5-Fold CV.
  * Liver Disease: 72.81% Holdout, 95.06% Sensitivity / Recall.
  * Thyroid: 100% Holdout, 95.81% $\pm$ 3.09% 5-Fold CV.
  * Malaria: 94.03% Strict Unseen Holdout Accuracy, 97.80% Recall, 95.70% F1.
* **Visual / Graphic:** Performance comparison bar chart / table.

---

### Slide 11: Controlled Synthetic Data Experiment
* **Key Points:**
  * Tested +25%, +50%, +100% synthetic tabular augmentations against real baseline data.
  * Strict holdout quarantine and in-fold cross-validation generation.
  * **Finding:** Synthetic augmentation degraded Liver holdout accuracy from 72.81% down to 66.67% and offered no benefit for clean linear boundaries.
  * **Decision:** Production system strictly uses models trained on real clinical data.
* **Visual / Graphic:** Synthetic vs. Real baseline performance trend graph.

---

### Slide 12: Cybersecurity & Privacy Architecture
* **Key Points:**
  * Cryptographic PBKDF2-HMAC-SHA256 password and PIN hashing.
  * Signed HMAC session tokens with strict IDOR defenses (Patient A $\leftrightarrow$ Patient B isolated).
  * Parameterized SQL queries preventing SQL injection.
  * Multi-stage Malaria image upload hardening (5MB limit, MIME check, OpenCV decodability).
  * Non-blocking online SQLite database backup routine.
* **Visual / Graphic:** Shield icon with 5 security defense pillars.

---

### Slide 13: Web Application & Clinical Workflow
* **Key Points:**
  * Patient Portal: Secure ID+PIN login, dashboard, reference range flags, printable report sheet.
  * Admin Portal: Patient registration, smart multi-panel report authoring (Draft vs. Finalized).
  * Decision Support Card: Distinct visual styling, confidence gauge, risk pill, and mandatory disclaimer.
  * Direct ML Sandbox: Interactive parameter testing and Malaria cell smear drag-and-drop.
* **Visual / Graphic:** Screenshot montage of Patient Portal, Report Sheet, and ML Sandbox.

---

### Slide 14: Automated Testing & Verification
* **Key Points:**
  * **25 / 25 Consolidated Test Scenarios Passing (100% Pass Rate).**
  * 15 Security & IDOR tests (Unauthorized access, IDOR attacks, SQLi, malicious uploads).
  * 10 Integration & ML pipeline tests (Patient lifecycle, report authoring, ML inferences).
  * Official report immutability bit-for-bit test passed.
* **Visual / Graphic:** Terminal test pass output banner (`Ran 25 tests ... OK`).

---

### Slide 15: Limitations, Future Scope & Conclusion
* **Key Points:**
  * **Limitations:** Limited public dataset sizes; models are decision support aids, not autonomous medical diagnoses.
  * **Future Scope:** Explainable AI (SHAP/LIME), HL7/FHIR interoperability, PostgreSQL migration, multi-factor authentication.
  * **Conclusion:** Nexus Pathology successfully unites modern digital pathology management with safe, decoupled, and empirically validated machine-learning decision support.
* **Visual / Graphic:** Thank You banner with Q&A callout.
