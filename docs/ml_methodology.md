# Machine Learning Methodology

The machine-learning subsystem of **Nexus Pathology** adheres to a disciplined data-science lifecycle to ensure reproducible, leakage-free, and clinically meaningful decision support.

---

## 1. Machine Learning Lifecycle Workflow

```
┌─────────────────┐
│ Raw Laboratory  │
│    Datasets     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Cleaning & │ ──> Handling missing values, categorical encoding,
│ Preprocessing   │     outlier inspection, schema harmonization
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stratified Split│ ──> 80% Training Set / 20% Holdout Test Set
│ (Zero Leakage)  │     (Fitted transformers strictly on train folds)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Algorithm Bench-│ ──> Logistic Regression, Random Forest, Gradient
│ mark & Tuning   │     Boosting, SVM, k-NN evaluated via 5-Fold CV
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Leakage &  │ ──> Target exclusion check, duplicate hash detection,
│ Integrity Audit │     cross-validation integrity verification
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Final Pipeline  │ ──> Serialized Scikit-Learn pipelines saved in
│ Serialization   │     models/ for FastAPI runtime execution
└─────────────────┘
```

---

## 2. Model Specialization Rationale

A unified "multi-disease" monolithic model was deliberately rejected in favor of **five specialized, independent pipelines**. This is because:
1. **Heterogeneous Input Feature Spaces:** A Complete Blood Count (CBC) examines cellular hematology (RBC, Platelets, MCV), while a Liver Function Test (LFT) evaluates hepatic enzymes (ALT, AST, ALP, Bilirubin). Forcing these disparate panels into a single model would result in massive feature sparsity and artificial imputation artifacts.
2. **Distinct Pathophysiological Mechanisms:** Anemia, Dengue, Hepatic Disease, Thyroid dysfunction, and Malaria parasite presence follow fundamentally different diagnostic trees and biomarker dynamics.
3. **Independent Validation & Maintenance:** Individual disease pipelines can be monitored, updated, or replaced independently without disrupting unrelated diagnostic panels.

---

## 3. Data Leakage Prevention Protocols

To ensure reported model metrics reflect true generalization performance:
* **Preprocessing Fit Boundary:** All scalers (e.g. `StandardScaler`) and categorical encoders (e.g. `OneHotEncoder`, `OrdinalEncoder`) were fitted exclusively on training sets and only applied as transforms on validation/holdout sets.
* **Target Feature Isolation:** Verification scripts confirmed target columns were never passed as inputs or used in intermediate feature transformations.
* **Cross-Validation In-Fold Preprocessing:** In 5-fold cross-validation, preprocessing pipelines were re-fitted within each training fold to prevent out-of-fold data leakage.
* **SHA-256 Duplicate Image Auditing:** For the Malaria microscopy dataset, cryptographic SHA-256 hashing was conducted across train and test partitions to identify and purge 25 duplicate images before final retraining.
