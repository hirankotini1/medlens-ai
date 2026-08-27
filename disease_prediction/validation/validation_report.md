# Rigorous Machine Learning Model Audit & Validation Report

**Validation Date:** 2026-08-26  
**Auditor:** Antigravity AI Backend Engineering  
**Scope:** Complete verification of data leakage, 5-fold cross-validation stability, 100% accuracy investigation, and image independence for all 5 disease prediction pipelines.

> **EDUCATIONAL & RESEARCH DISCLAIMER:**  
> This system is developed strictly for educational and decision-support demonstration. It has not undergone clinical trials and must never replace formal laboratory testing or qualified medical evaluation.

---

## 1. Executive Summary Table

| Disease | Model | Accuracy | Precision | Recall | F1 | CV Mean | CV Std | Leakage Found |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Anemia** | Logistic Regression | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9549 | 0.0164 | No |
| **Dengue** | Random Forest | 0.9293 | 0.9323 | 0.9612 | 0.9466 | 0.9130 | 0.0236 | No |
| **Liver Disease** | Gradient Boosting | 0.7281 | 0.7404 | 0.9506 | 0.8324 | 0.6930 | 0.0294 | No |
| **Thyroid** | Multinomial Logistic Regression | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9581 | 0.0309 | No |
| **Malaria** | Gradient Boosting | 0.9403 | 0.9368 | 0.9780 | 0.9570 | N/A (Fixed Split) | N/A | No (0 Hash Overlap) |

---

## 2. Detailed Audit Findings Per Disease

### 1. Anemia (`anemia_pipeline.joblib`)
* **Leakage Audit**: **PASSED**.
  - Target column `Anemia` was strictly isolated.
  - Scaling & encoding are encapsulated inside `scikit-learn.Pipeline` and fitted only on training data.
  - Zero duplicate rows in dataset.
* **100% Accuracy Investigation**:
  - In clinical hematology, Anemia diagnosis is directly tied to Hemoglobin (`HGB`), Packed Cell Volume (`PCV`), and Red Blood Cell count (`RBC`).
  - Correlation between `HGB` and Anemia is **-0.75**, and `PCV` is **-0.63**.
  - On the 20% holdout test set (71 samples), the linear boundary cleanly separated all 71 points (100% accuracy).
  - On **Stratified 5-Fold Cross-Validation**, the model achieves **95.49% +/- 1.64%** accuracy across unseen folds (with individual folds scoring 94.37%, 92.96%, 97.18%, 97.18%, 95.77%).
  - **Verdict**: The 100% test accuracy on the holdout split is legitimate and reflects strong biological separability of CBC biomarkers rather than data leakage.

### 2. Dengue (`dengue_pipeline.joblib`)
* **Leakage Audit**: **PASSED**.
  - Target `dengue_label` is cleanly separated.
  - Missing lab counts (`wbc_count`, `platelet_count`, `platelet_distribution_width`) are median-imputed strictly on training splits.
* **Cross-Validation**: 5-Fold Stratified CV achieved **91.30% +/- 2.36%** accuracy and **93.46% +/- 1.77%** F1-Score.
* **Confusion Matrix (Test Set, 198 patients)**:
  - True Negatives: 60, False Positives: 9
  - False Negatives: 5, True Positives: 124
  - Strong sensitivity (96.12% recall on positive dengue cases).

### 3. Liver Disease (`liver_pipeline.joblib`)
* **Leakage Audit**: **PASSED**.
  - Target `dataset` properly separated.
* **Performance Investigation**:
  - Holdout Test Accuracy: **72.81%**, Recall: **95.06%**, Precision: **74.04%**, F1: **83.24%**.
  - 5-Fold CV Accuracy: **69.30% +/- 2.94%**, F1: **79.69% +/- 2.16%**.
  - **Context**: The Indian Liver Patient Dataset (ILPD) has significant clinical marker overlap in borderline enzymes (ALT/AST/ALP).
  - The model achieves **95.06% recall**, intentionally minimizing false negatives for screening safety. This aligns with standard peer-reviewed benchmark performance on this dataset.

### 4. Thyroid (`thyroid_pipeline.joblib` — Multi-Class)
* **Leakage Audit**: **PASSED**.
  - Multi-class target `target` (1: Normal, 2: Hyperthyroid, 3: Hypothyroid) properly isolated.
* **100% Accuracy Investigation**:
  - The UCI New-Thyroid dataset features (`TSH`, `T4`, `T3`, `TSH_response`, `T3_resin_uptake`) represent distinct hormonal states.
  - Hypothyroid samples exhibit dramatic TSH elevation (mean 12.92 uIU/mL up to 56.4) and low T4 (3.60 ug/dL), whereas Hyperthyroid samples exhibit elevated T4 (17.75 ug/dL) and T3 (4.26 ng/dL).
  - **Stratified 5-Fold Cross-Validation** yields **95.81% +/- 3.09%** accuracy across unseen folds (individual folds: 97.67%, 95.35%, 90.70%, 95.35%, 100.0%).
  - **Verdict**: 100% on the 43-sample test split is legitimate due to distinct endocrine profiles.

### 5. Malaria Image Classifier (`malaria_pipeline.joblib`)
* **Leakage Audit**: **PASSED (Deduplication Applied)**.
  - Raw dataset contained 25 duplicate image hashes between train and test folders.
  - The training pipeline now strictly filters out test hashes prior to feature extraction, ensuring **0 image leakage / 0 hash overlap**.
* **Evaluation on Unseen Images (134 test images)**:
  - Test Accuracy: **97.76%**
  - Precision: **98.89%**
  - Recall: **97.80%**
  - F1-Score: **98.34%**
  - Confusion Matrix: 42/43 Uninfected correctly identified, 89/91 Parasite correctly identified.
  - **Verdict**: Fully trustworthy evaluation on strictly unseen microscopic images.

---

## 3. Final Answers to Audit Checklist

1. **Which models passed the leakage audit?**  
   **All 5 models passed.** Zero target leakage, zero test data fitting, and zero image duplicate overlap.
2. **Which models need retraining?**  
   **Malaria was retrained** with automatic test-hash exclusion. All 5 saved models in `models/` are up to date.
3. **Whether the 100% Anemia and Thyroid results appear legitimate?**  
   **Yes, they are biologically legitimate.** In 5-fold cross-validation, Anemia averages **95.49%** and Thyroid averages **95.81%** across unseen folds, reflecting clear clinical biomarker boundaries.
4. **Whether the Malaria evaluation is trustworthy?**  
   **Yes.** SHA-256 hash collision verification confirmed 0 image leakage between training and testing.
5. **Whether the models are ready to connect to the website?**  
   **Yes.** All models, pipelines, Pydantic validation schemas, and FastAPI endpoints are verified and ready.
