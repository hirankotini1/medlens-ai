# Dataset Description & Feature Engineering

This document specifies the input features, biological significance, data types, and target distributions for the five disease prediction modules.

---

## 1. Anemia (Complete Blood Count Panel)

* **Dataset Size:** 1,421 samples
* **Target Classes:** Binary — `0: Non-Anemic (Normal)`, `1: Anemic`
* **Features (11):**

| Feature Name | Type | Clinical Unit | Biological Significance |
|---|---|---|---|
| `Age` | Numerical | Years | Baseline physiological age |
| `Sex` | Categorical | Male/Female | Sex-adjusted physiological hemoglobin baseline |
| `HGB` | Numerical | g/dL | Hemoglobin concentration in whole blood |
| `RBC` | Numerical | $10^{12}$/L | Total red blood cell count |
| `PCV` | Numerical | % | Packed Cell Volume (Hematocrit) |
| `MCV` | Numerical | fL | Mean Corpuscular Volume (Average erythrocyte size) |
| `MCH` | Numerical | pg | Mean Corpuscular Hemoglobin |
| `MCHC` | Numerical | g/dL | Mean Corpuscular Hemoglobin Concentration |
| `RDW` | Numerical | % | Red Cell Distribution Width (Erythrocyte size variation) |
| `TLC` | Numerical | $10^3$/$\mu$L | Total Leukocyte (WBC) Count |
| `PLT /mm3` | Numerical | $/mm^3$ | Platelet Count |

---

## 2. Dengue (Hematology & Platelet Dynamics)

* **Dataset Size:** 1,000 samples
* **Target Classes:** Binary — `0: Negative / Normal`, `1: Dengue Positive`
* **Features (8):**

| Feature Name | Type | Clinical Unit | Biological Significance |
|---|---|---|---|
| `age` | Numerical | Years | Patient age |
| `gender` | Categorical | Male/Female/Child | Demographic cohort |
| `hemoglobin_g_dl` | Numerical | g/dL | Hemoconcentration indicator |
| `wbc_count` | Numerical | cells/$\mu$L | Leukocyte kinetics (Leukopenia detection) |
| `differential_count` | Categorical | Flag (0/1) | Differential lymphocyte shift flag |
| `rbc_count` | Categorical | Flag (0/1) | RBC morphology indicator |
| `platelet_count` | Numerical | cells/$\mu$L | Critical thrombocytopenia indicator |
| `platelet_distribution_width`| Numerical | % | Platelet volume variation |

---

## 3. Liver Disease (Hepatic Function Panel - LFT)

* **Dataset Size:** 583 samples (Indian Liver Patient Dataset - ILPD)
* **Target Classes:** Binary — `1: Liver Disease`, `2: Non-Liver Disease`
* **Features (10):**

| Feature Name | Type | Clinical Unit | Biological Significance |
|---|---|---|---|
| `age` | Numerical | Years | Patient age |
| `gender` | Categorical | Male/Female | Gender |
| `total_bilirubin` | Numerical | mg/dL | Total serum bilirubin (Hepatobiliary excretion) |
| `direct_bilirubin` | Numerical | mg/dL | Conjugated bilirubin |
| `alkaline_phosphotase` | Numerical | IU/L | ALP enzyme (Biliary tract indicator) |
| `alamine_aminotransferase` | Numerical | IU/L | ALT / SGPT (Hepatocellular injury indicator) |
| `aspartate_aminotransferase`| Numerical | IU/L | AST / SGOT (Hepatic enzyme) |
| `total_protiens` | Numerical | g/dL | Total serum protein concentration |
| `albumin` | Numerical | g/dL | Serum albumin (Synthetic liver function) |
| `albumin_and_globulin_ratio`| Numerical | Ratio | A/G Ratio |

---

## 4. Thyroid Hormone Profile

* **Dataset Size:** 3,772 samples
* **Target Classes:** 3 Classes — `1: Normal (Euthyroid)`, `2: Hyperthyroid`, `3: Hypothyroid`
* **Features (5):**

| Feature Name | Type | Clinical Unit | Biological Significance |
|---|---|---|---|
| `TSH` | Numerical | $\mu$IU/mL | Thyroid Stimulating Hormone (Primary screening metric) |
| `T4` | Numerical | $\mu$g/dL | Total Thyroxine hormone |
| `T3` | Numerical | ng/dL | Triiodothyronine hormone |
| `TSH_response` | Numerical | Score | Pituitary TSH responsiveness to TRH |
| `T3_resin_uptake` | Numerical | % | Binding protein saturation percentage |

---

## 5. Malaria Microscopy (Cell Image Features)

* **Dataset Size:** NIH / Kaggle Malaria Cell Images dataset (Thin blood smears)
* **Target Classes:** Binary — `0: Uninfected RBC`, `1: Parasitized RBC` (Plasmodium presence)
* **Feature Extraction Subsystem (`MalariaFeatureExtractor`):**
  * Transforms raw cell images ($100\times100\times3$) into a **354-dimensional feature vector**:
    1. **Color Statistics:** Mean, standard deviation, skewness, and kurtosis across BGR, HSV, and LAB color channels (36 features).
    2. **Color Histograms:** Multi-bin color distributions across HSV and LAB spaces (256 features).
    3. **Morphology & Texture:** Hu Moments and Gray-Level Co-occurrence Matrix (GLCM) texture descriptors (62 features).
