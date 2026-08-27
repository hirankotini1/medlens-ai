# Project Abstract

**Project Title:** Nexus Pathology — Digital Pathology Laboratory Management Platform with Experimental Machine-Learning Decision Support  
**Domain:** Healthcare Informatics, Web Engineering & Applied Machine Learning  

---

## Abstract

Clinical pathology laboratories generate large volumes of diagnostic data essential for medical evaluations. Traditional laboratory workflows often rely on physical paper records or siloed electronic systems with limited patient accessibility and no integrated computational decision support. Furthermore, applying machine learning to clinical workflows introduces challenges around data privacy, report integrity, and diagnostic overreach.

**Nexus Pathology** is a web-based digital pathology laboratory management platform integrated with an experimental machine-learning (ML) decision-support backend. The platform provides a secure, role-based environment with two primary interfaces:
1. **Administrative & Laboratory Staff Portal:** Facilitates patient registration, structured test parameter recording, report lifecycle management (Draft vs. Finalized), and on-demand execution of experimental ML decision support.
2. **Patient Portal:** Provides authenticated, privacy-preserving access for patients to view their official laboratory findings, reference ranges, pathologist remarks, and separate experimental ML analysis summaries.

The system incorporates five independently trained and validated machine-learning pipelines tailored to specific pathological investigations:
* **Complete Blood Count (CBC) / Anemia:** Logistic Regression (11 features)
* **Dengue Hematology Profile:** Random Forest Classifier (8 features)
* **Liver Function Test (LFT):** Gradient Boosting Classifier (10 features)
* **Thyroid Hormone Profile:** Multinomial Logistic Regression (5 features)
* **Malaria Microscopy Smear:** Computer Vision Feature Extractor combined with Gradient Boosting (354-dimensional color and texture feature vector)

A core architectural principle of Nexus Pathology is the **strict decoupling of official laboratory reports from ML predictions**. Official pathology findings remain immutable and authoritative within the primary database, while ML predictions are stored separately in an independent audit log. Every ML prediction displays the model version, calculated confidence score, risk indicator, and an explicit educational/research disclaimer stating that computational predictions serve solely as decision support and do not constitute an autonomous medical diagnosis.

The platform is implemented using a Python FastAPI REST backend, a lightweight SQLite relational database with parameterized queries, and a modern responsive HTML5/CSS3/JavaScript interface. Security controls include cryptographic PBKDF2-HMAC-SHA256 password and PIN hashing, HMAC-signed session tokens, Role-Based Access Control (RBAC), and strict defenses against Insecure Direct Object References (IDOR). Comprehensive testing—comprising unit, integration, and security test suites totaling 25 distinct verification scenarios—validates the functional reliability and security posture of the platform for academic and demonstration purposes.
