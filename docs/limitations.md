# Limitations

In adherence to ethical and academic standards in artificial intelligence for healthcare, the limitations of the current implementation are explicitly documented:

---

## 1. Machine Learning & Dataset Constraints

* **Limited Dataset Sample Sizes:** Datasets used for training (e.g. 583 samples for Liver Disease, 1,421 samples for Anemia) represent finite public cohorts and may not fully reflect geographical, genetic, and epidemiological diversity.
* **No Multi-Center External Validation:** Models have not yet been evaluated against prospective, multi-institutional clinical cohorts outside the original benchmark datasets.
* **Dataset Performance $\neq$ Real-World Clinical Accuracy:** High holdout accuracy (such as 100% in Anemia or Thyroid) reflects statistical separability in the curated dataset and must not be interpreted as absolute diagnostic certainty.
* **Hepatic Panel Overlap:** The Liver Disease dataset exhibits significant biological overlap, resulting in lower holdout accuracy (72.81%) compared to the other tabular models, although sensitivity (95.06%) was prioritized.
* **Microscopy Domain Sensitivity:** The Malaria model operates on single-cell cropped microscopy images and requires standardized Giemsa staining and magnification for optimal inference.

---

## 2. Clinical & Regulatory Boundaries

* **No Regulatory Approval:** The platform is not certified as Software as a Medical Device (SaMD) by regulatory authorities (e.g., FDA, CE-IVD, CDSCO).
* **Decision Support Only:** Machine-learning predictions cannot replace comprehensive diagnostic evaluations, clinical history examinations, or physical consultations by qualified medical professionals.

---

## 3. Infrastructure & Deployment Boundaries

* **Local Database Engine:** SQLite is optimized for local demonstration, single-server instances, and academic review. Large enterprise hospital deployments with high concurrent read/write loads require client-server RDBMS engines (such as PostgreSQL).
* **Network Security Prerequisites:** Public internet hosting requires reverse proxy infrastructure (Nginx/Caddy) with TLS/HTTPS certificate termination and IP-based rate limiting.
