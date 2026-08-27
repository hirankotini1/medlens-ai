# Final Machine Learning Model Results & Performance Evaluation

All metrics reported in this document represent strictly validated benchmarks obtained from untouched holdout test sets and rigorous 5-fold cross-validation.

---

## 1. Summary of Validated Production Models

| Disease / Panel | Selected Algorithm | Input Dimensionality | Holdout Accuracy | 5-Fold Cross-Validation | Primary Clinical Metric |
|---|---|:---:|:---:|:---:|---|
| **Anemia (CBC)** | Logistic Regression | 11 Features | **100.00%** | **95.49% $\pm$ 1.64%** | F1-Score: 100% |
| **Dengue** | Random Forest Classifier | 8 Features | **92.93%** | **91.30% $\pm$ 2.36%** | Recall: 93.10% |
| **Liver Disease** | Gradient Boosting | 10 Features | **72.81%** | **69.30% $\pm$ 2.94%** | **Recall: 95.06%** |
| **Thyroid Profile** | Multinomial Logistic Regression | 5 Features | **100.00%** | **95.81% $\pm$ 3.09%** | Multi-class F1: 100% |
| **Malaria (Image)** | Gradient Boosting + CV Extractor | 354 Features | **94.03%** | *Strict Unseen Holdout* | **Recall: 97.80%** |

---

## 2. Detailed Disease-by-Disease Performance Analysis

### A. Anemia Detection (Complete Blood Count)
* **Holdout Set Performance:** 100% Accuracy on the 285-sample holdout test partition.
* **Cross-Validation Performance:** 5-Fold CV yielded $95.49\% \pm 1.64\%$, demonstrating robust stability across multiple train-test folds.
* **Interpretation:** Hematological parameters (specifically Hemoglobin, PCV, MCV, and MCH) possess strong, well-defined linear separation boundaries for classical anemia classification, making regularized Logistic Regression optimal and interpretable.

### B. Dengue Fever Risk
* **Holdout Set Performance:** 92.93% Accuracy, 93.10% Recall, 92.90% F1-Score on the 198-sample test partition.
* **Cross-Validation Performance:** 5-Fold CV yielded $91.30\% \pm 2.36\%$.
* **Interpretation:** Random Forest effectively captures non-linear interactions between sharp platelet drops (thrombocytopenia) and acute leukocyte shifts (leukopenia).

### C. Liver Disease Diagnosis
* **Holdout Set Performance:** 72.81% Accuracy, 73.08% Precision, **95.06% Recall**, 82.60% F1-Score on the 114-sample test partition.
* **Cross-Validation Performance:** 5-Fold CV yielded $69.30\% \pm 2.94\%$.
* **Interpretation:** Hepatic function panels exhibit substantial natural biological overlap between borderline patients and non-liver controls. Gradient Boosting was specifically calibrated to maximize **Sensitivity / Recall (95.06%)**, prioritizing the minimization of dangerous False Negatives in clinical decision support.

### D. Thyroid Hormone Profile
* **Holdout Set Performance:** 100% Accuracy across all 3 classes (Normal, Hyperthyroid, Hypothyroid) on the 755-sample test partition.
* **Cross-Validation Performance:** 5-Fold CV yielded $95.81\% \pm 3.09\%$.
* **Interpretation:** TSH and free thyroid hormones (T3, T4) exhibit distinct cluster separation in log-linear space, enabling highly reliable multinomial classification.

### E. Malaria Microscopy Smear (Image Analysis)
* **Dataset Audit & Deduplication:** A cryptographic SHA-256 duplicate audit detected 25 duplicate images between the original train and test sets. These duplicates were purged, and the model was retrained and evaluated on strictly distinct unseen cell images.
* **Strict Unseen Test Performance:**
  * **Accuracy:** **94.03%**
  * **Precision:** **93.68%**
  * **Sensitivity / Recall:** **97.80%**
  * **F1-Score:** **95.70%**
* **Interpretation:** The 354-dimensional color and moment feature vector accurately isolates Giemsa-stained intra-erythrocytic ring stages and trophozoites with high diagnostic sensitivity (97.80% Recall).

---

> **Academic Note on 100% Holdout Results:** Perfect holdout scores in Anemia and Thyroid reflect dataset-specific separability and must not be misinterpreted as 100% real-world diagnostic certainty. The 5-fold cross-validation figures ($95.49\%$ and $95.81\%$) provide a more realistic estimate of generalized performance across varying cohorts.
