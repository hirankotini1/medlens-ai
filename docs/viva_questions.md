# Comprehensive College Viva Questions & Answers (55 Questions)

A categorized collection of 55 technical, architectural, machine learning, security, and ethical questions with simple, direct answers for college project viva examinations.

---

## Category 1: Project & Architecture

### Q1: What is Nexus Pathology?
**Answer:** Nexus Pathology is a web-based digital pathology laboratory management platform combined with an experimental machine-learning decision-support backend for five disease categories.

### Q2: Why did you choose this project?
**Answer:** To solve real-world healthcare workflow problems—such as lost physical records, lack of secure patient access, and absence of computational assistance—while safely integrating AI decision support without altering official medical records.

### Q3: What problem does it solve?
**Answer:** It digitizes manual laboratory workflows, provides authenticated patient access, structures biochemical data with reference ranges, and provides decoupled computational decision support.

### Q4: What are the main modules of the application?
**Answer:** 
1. Patient Portal (Authentication, dashboard, report viewing, printing)
2. Admin / Lab Staff Portal (Patient registration, smart report authoring, lifecycle management)
3. Experimental ML Decision Support Engine (5 disease pipelines)
4. Direct ML Testing Sandbox
5. Security, RBAC & Audit Logging Subsystem

### Q5: Why is it called "Decision Support" rather than a "Diagnosis System"?
**Answer:** Because AI algorithms provide statistical pattern estimates. In medical informatics, AI must serve as an assistive decision-support tool for clinicians rather than an autonomous medical authority.

---

## Category 2: Database & Data Modeling

### Q6: Why did you use SQLite for this project?
**Answer:** SQLite is serverless, zero-configuration, lightweight, ACID-compliant, and built into Python, making it ideal for local demonstration, testing, and academic evaluation.

### Q7: What are the core tables in your database?
**Answer:**
1. `patients` — Stores patient demographics and hashed security PINs.
2. `lab_reports` — Stores official clinical findings, biological reference ranges, and doctor remarks.
3. `ml_predictions` — Stores an immutable audit trail of all ML inferences.
4. `users` — Stores laboratory staff credentials and roles.

### Q8: Why are ML predictions stored in a separate table from official reports?
**Answer:** Official laboratory reports are legal medical documents that must remain immutable. Storing ML predictions in a separate `ml_predictions` table prevents data corruption, ensures historical auditability, and allows safe model updates.

### Q9: What is the relationship between patients and laboratory reports?
**Answer:** A One-to-Many (1:N) relationship. One patient can have multiple laboratory reports over time, linked via the `patient_id` foreign key.

### Q10: How are clinical metrics stored in the database?
**Answer:** Parameter values, units, biological reference intervals, and abnormality flags are stored as structured JSON inside the `report_data` column of `lab_reports`.

---

## Category 3: Backend & Web API

### Q11: Why did you choose FastAPI over Flask or Django?
**Answer:** FastAPI provides high asynchronous performance (ASGI), automatic Pydantic data validation, type hints, and automatic OpenAPI (Swagger) documentation generation.

### Q12: What is an API?
**Answer:** An Application Programming Interface (API) is a set of defined rules and protocols that allow the frontend client to communicate with the backend server.

### Q13: What is a REST API?
**Answer:** A stateless web architecture that uses standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`) to transfer structured resources (usually JSON).

### Q14: What is an API endpoint?
**Answer:** A specific URL location on a server (e.g. `/api/reports`) where client applications send requests to perform operations.

### Q15: What role does Pydantic play in your backend?
**Answer:** Pydantic enforces strict runtime data validation. It checks data types, required fields, and numerical boundaries (e.g., rejecting negative hemoglobin values).

### Q16: What is CORS and how is it handled?
**Answer:** Cross-Origin Resource Sharing (CORS) is a browser security mechanism that restricts cross-domain HTTP requests. In FastAPI, `CORSMiddleware` manages authorized origins and methods.

---

## Category 4: Frontend & UI Design

### Q17: Why did you use Vanilla CSS and JavaScript instead of heavy frameworks?
**Answer:** Vanilla HTML5, CSS3, and ES6+ JavaScript keep the application ultra-lightweight, fast-loading, dependency-free, and easy to maintain while providing maximum control over custom aesthetics.

### Q18: How does the application handle printable reports?
**Answer:** Using a dedicated `@media print` CSS stylesheet that hides web navigation and buttons, formatting the official findings into a clean physical pathology sheet.

### Q19: How are abnormality flags determined in the UI?
**Answer:** The system compares observed biomarker values against clinical biological reference intervals and assigns color-coded badges (`Normal`, `Low`, `High`, `Critical`).

---

## Category 5: Machine Learning Concepts & Preprocessing

### Q20: What is Machine Learning?
**Answer:** A branch of artificial intelligence where computer algorithms learn statistical patterns from historical data to make predictions without being explicitly hardcoded.

### Q21: Why did you build separate models for each disease?
**Answer:** Because each disease panel evaluates different biological parameters (e.g. CBC measures blood cells, LFT measures liver enzymes). Combining them into one model would cause severe feature sparsity and imputation errors.

### Q22: What is a train-test split?
**Answer:** Partitioning a dataset into a training subset (80%) used to train the algorithm and an untouched holdout test subset (20%) used to evaluate performance on unseen data.

### Q23: What is 5-fold cross-validation?
**Answer:** Dividing training data into 5 equal folds, training on 4 folds and testing on the 5th, repeated 5 times. The average score reflects model stability across different data subsets.

### Q24: What is data leakage, and how did you prevent it?
**Answer:** Data leakage occurs when test information influences training. We prevented it by fitting all scalers and encoders strictly on training folds, excluding target labels from input matrices, and running duplicate audits.

---

## Category 6: Datasets & Features

### Q25: What datasets did you use?
**Answer:** Curated, publicly available clinical datasets for Anemia (Complete Blood Count), Dengue (Hematology & Platelets), Indian Liver Patient Dataset (ILPD), Thyroid Hormone Profiles, and the NIH Malaria Cell Images dataset.

### Q26: What features are used for Anemia prediction?
**Answer:** 11 CBC features: Age, Sex, Hemoglobin (HGB), RBC Count, Packed Cell Volume (PCV), MCV, MCH, MCHC, RDW, TLC (WBC), and Platelet Count.

### Q27: What features are used for Dengue prediction?
**Answer:** 8 hematology features: Age, Gender, Hemoglobin, WBC Count, Differential Count flag, RBC Morphology flag, Platelet Count, and Platelet Distribution Width (PDW).

### Q28: What features are used for Liver Disease prediction?
**Answer:** 10 LFT features: Age, Gender, Total Bilirubin, Direct Bilirubin, Alkaline Phosphatase (ALP), ALT/SGPT, AST/SGOT, Total Proteins, Albumin, and A/G Ratio.

### Q29: What features are used for Thyroid prediction?
**Answer:** 5 hormone features: TSH, Free T4, T3, TSH Response to TRH, and T3 Resin Uptake.

---

## Category 7: Algorithms & Selection

### Q30: Why did Anemia use Logistic Regression?
**Answer:** Hematological indices have strong linear separability for anemia. Logistic Regression achieved 100% holdout accuracy and 95.49% 5-fold CV while offering high computational interpretability.

### Q31: Why did Dengue use Random Forest?
**Answer:** Random Forest is an ensemble of decision trees that excels at capturing non-linear interactions between sharp platelet drops (thrombocytopenia) and acute leukocyte shifts without overfitting.

### Q32: Why did Liver Disease use Gradient Boosting?
**Answer:** Hepatic panels have complex, overlapping biomarker distributions. Gradient Boosting iteratively trains decision trees to minimize classification errors and was calibrated for high **Sensitivity / Recall (95.06%)**.

### Q33: Why did Thyroid use Multinomial Logistic Regression?
**Answer:** The Thyroid task involves three mutually exclusive classes (Normal, Hyperthyroid, Hypothyroid). Multinomial Logistic Regression uses the softmax function to output calibrated multi-class probabilities.

---

## Category 8: Evaluation Metrics

### Q34: What is Precision?
**Answer:** The proportion of predicted positive cases that are truly positive ($\text{TP} / (\text{TP} + \text{FP})$).

### Q35: What is Recall (Sensitivity)?
**Answer:** The proportion of actual positive cases correctly identified by the model ($\text{TP} / (\text{TP} + \text{FN})$).

### Q36: Why is Recall critical in medical machine learning?
**Answer:** Because a False Negative (missing a sick patient) can be life-threatening, whereas a False Positive can be caught during subsequent confirmatory clinical tests.

### Q37: What is the F1-Score?
**Answer:** The harmonic mean of Precision and Recall ($2 \times (\text{Precision} \times \text{Recall}) / (\text{Precision} + \text{Recall})$), providing a balanced measure on imbalanced data.

### Q38: How should 100% holdout accuracy in Anemia and Thyroid be interpreted?
**Answer:** It reflects high linear separability in the curated dataset partitions. In clinical presentations, cross-validation scores ($95.49\%$ and $95.81\%$) should be cited as more realistic generalized benchmarks.

---

## Category 9: Synthetic Data Augmentation

### Q39: What is synthetic tabular data?
**Answer:** Artificially generated numerical records that statistically mimic real data distributions.

### Q40: Why did you conduct a synthetic data experiment?
**Answer:** To empirically test whether adding synthetic samples (+25%, +50%, +100%) would improve model generalization on real holdout test sets.

### Q41: What were the results of the synthetic data experiment?
**Answer:** Real baseline models matched or outperformed augmented models. In Liver Disease, 100% synthetic augmentation degraded holdout accuracy from 72.81% down to 66.67%.

### Q42: Why was synthetic data NOT used in production?
**Answer:** Because empirical evidence showed it introduced boundary noise rather than improving real-world generalization. Production models are strictly trained on real clinical data.

---

## Category 10: Cybersecurity & Patient Privacy

### Q43: What is Authentication vs. Authorization?
**Answer:** Authentication verifies *who the user is* (valid ID & PIN). Authorization verifies *what resources the user can access* (patients can only view their own reports).

### Q44: What is Role-Based Access Control (RBAC)?
**Answer:** Restricting API endpoints based on user roles (`admin` vs. `patient`), preventing patients from accessing administrative routes.

### Q45: What is an Insecure Direct Object Reference (IDOR) attack?
**Answer:** An attack where a user alters an ID parameter in a URL or request to view another patient's private records without authorization.

### Q46: How does your system prevent IDOR attacks?
**Answer:** Every incoming token is verified. If a patient token requests a `patient_id` or `report_id` that does not match their verified identity, the server returns an immediate HTTP 403 Forbidden.

### Q47: How are passwords and security PINs protected?
**Answer:** Using PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salts. Plaintext credentials are never stored.

### Q48: How are SQL Injection attacks prevented?
**Answer:** By using parameterized SQL queries with `?` placeholders across all database queries, completely eliminating string concatenation.

---

## Category 11: Malaria Image Processing

### Q49: Why is Malaria an image classification problem?
**Answer:** Because malaria diagnosis is performed by microscopic visual examination of Giemsa-stained thin blood smears to detect intra-erythrocytic Plasmodium parasites.

### Q50: How does the Malaria feature extractor work?
**Answer:** It extracts a 354-dimensional feature vector combining color channel statistics (BGR, HSV, LAB), color histograms, Hu shape moments, and GLCM texture descriptors from cell images.

### Q51: What did the Malaria dataset leakage audit discover?
**Answer:** A SHA-256 hash audit detected 25 duplicate images between the original train and test sets. Purging these duplicates ensured strict unseen testing (94.03% accuracy, 97.80% recall).

---

## Category 12: Healthcare Ethics & Governance

### Q52: Can this system replace a doctor or pathologist?
**Answer:** No. Machine learning assists with pattern recognition, but clinical diagnosis requires comprehensive physical examination, medical history, and clinical judgment by a licensed physician.

### Q53: What happens if a laboratory report is missing required values when ML is run?
**Answer:** The system does not guess or silently impute missing data. It rejects the ML request with a descriptive HTTP 422 error, listing the missing fields, while keeping the official report accessible.

---

## Category 13: Limitations & Future Scope

### Q54: What are the main limitations of the system?
**Answer:** Limited dataset sample sizes, absence of multi-center prospective clinical trials, and lack of formal medical device regulatory certification.

### Q55: What would you improve in the future?
**Answer:** Add Explainable AI (SHAP/LIME) feature attribution plots, implement HL7/FHIR v4 interoperability for hospital EHRs, migrate to PostgreSQL, and add multi-factor authentication.
