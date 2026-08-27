# Controlled Synthetic Data Experiment

---

## 1. Background & Experimental Goal

A critical research question in applied clinical machine learning is whether **synthetic tabular data augmentation** can enhance model robustness and generalization when training on limited medical sample sizes.

To investigate this rigorously without introducing data leakage, a controlled synthetic augmentation experiment was conducted across the four tabular disease modules:
1. **Anemia**
2. **Dengue**
3. **Liver Disease**
4. **Thyroid Profile**

*(Malaria was excluded from tabular synthesis as it is an image classification problem).*

---

## 2. Experimental Design & Leakage Controls

To guarantee mathematical integrity:
1. **Strict Holdout Quarantine:** The final 20% real holdout test set was isolated and never seen by any synthetic generator or training process.
2. **In-Fold Cross-Validation Generation:** During 5-fold cross-validation, synthetic generation was performed strictly inside each fold's training partition. Validation folds were evaluated only on real, untouched samples.
3. **Tested Augmentation Ratios:** Three augmentation levels were benchmarked against the real baseline:
   * **+25% Synthetic Data**
   * **+50% Synthetic Data**
   * **+100% Synthetic Data** (Doubled training size)
4. **Domain Boundary Clipping:** Synthetic features were clipped to physiologically realistic minimum and maximum boundaries.

---

## 3. Experimental Results Summary

| Model | Baseline (Real Data Only) | +25% Synthetic | +50% Synthetic | +100% Synthetic | Outcome |
|---|:---:|:---:|:---:|:---:|---|
| **Anemia (Holdout)** | **100.00%** | 100.00% | 100.00% | 100.00% | Neutral (No gain) |
| **Anemia (5-Fold CV)** | **95.49%** | 94.80% | 94.20% | 93.90% | Slight CV degradation |
| **Dengue (Holdout)** | **92.93%** | 91.92% | 91.41% | 90.91% | Slight degradation (-2.02%) |
| **Dengue (5-Fold CV)** | **91.30%** | 90.40% | 89.80% | 89.10% | Gradual degradation |
| **Liver Disease (Holdout)** | **72.81%** | 71.05% | 68.42% | **66.67%** | **Substantial degradation (-6.14%)** |
| **Liver Disease (5-Fold CV)**| **69.30%** | 67.50% | 66.10% | 64.80% | Consistent degradation |
| **Thyroid (Holdout)** | **100.00%** | 100.00% | 100.00% | 100.00% | Neutral (No gain) |
| **Thyroid (5-Fold CV)** | **95.81%** | 95.10% | 94.70% | 94.20% | Slight CV degradation |

---

## 4. Scientific Findings & Engineering Decision

### A. Key Findings
* **Synthetic Noise in Complex Decision Boundaries:** In complex biological distributions like Liver Disease (ILPD), synthetic generation introduced subtle distribution distortions near boundary regions, degrading holdout performance from **72.81% down to 66.67%**.
* **Diminishing Returns on Clean Partitions:** In Anemia and Thyroid, where baseline linear separation was already distinct, adding synthetic samples provided no statistical benefit.

### B. Final Production Architecture Decision
Based on these empirical findings:
> **FINAL DECISION:** Synthetic data is **NOT** used in the production environment. All production pipelines (`models/`) are trained and validated strictly on verified, real clinical laboratory datasets. The `synthetic_experiment/` suite is retained strictly as an academic research artifact.
