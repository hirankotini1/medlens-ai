# Project Objectives

The primary objective of **Nexus Pathology** is to design, develop, and evaluate a secure, web-based digital pathology laboratory management platform integrated with an experimental machine-learning decision-support backend.

---

## Specific Objectives

1. **Digitize Pathology Workflow:** Develop an administrative workflow for laboratory technicians and pathologists to register patients, enter structured laboratory metrics across five test categories, and manage report lifecycle statuses (Draft vs. Finalized).
2. **Provide Secure Patient Access:** Implement a patient portal allowing authenticated users to securely retrieve their official pathology findings with biological reference ranges, abnormality flags, and doctor remarks.
3. **Ensure Patient Data Isolation & IDOR Defenses:** Enforce strict access control mechanisms so that patients can strictly view only their own records, rejecting cross-patient access attempts with HTTP 403 Forbidden.
4. **Decouple Official Findings from ML Predictions:** Architect a database schema where authoritative laboratory reports (`lab_reports`) remain immutable and independent of probabilistic machine-learning predictions (`ml_predictions`).
5. **Develop Five Independent ML Pipelines:** Train, validate, and serialize five specialized machine-learning pipelines addressing Anemia, Dengue, Liver Disease, Thyroid Disorders, and Malaria cell microscopy.
6. **Rigorous Validation & Cross-Validation:** Evaluate all models using appropriate classification metrics (Accuracy, Precision, Recall, F1-Score, and 5-Fold Cross-Validation) and conduct data leakage audits to ensure zero train-test contamination.
7. **Investigate Synthetic Data Augmentation:** Conduct a controlled experiment evaluating whether synthetic tabular data augmentation enhances model generalization, establishing an evidence-based decision for production deployment.
8. **Provide Safe Experimental ML Decision Support:** Render model outputs in a visually distinct decision-support card featuring confidence gauges, risk level indicators, model provenance, and mandatory educational/research disclaimers.
9. **Maintain an Immutable Prediction Audit Log:** Persist all generated ML inferences with full metadata snapshots (input values, model version, timestamp, confidence) for clinical auditability.
10. **Implement Robust Cybersecurity Controls:** Enforce PBKDF2-HMAC-SHA256 password and PIN hashing, HMAC-signed session tokens, parameterized SQL queries, strict image upload validation (5MB cap, MIME verification, dimension checks), and automated database backup routines.
