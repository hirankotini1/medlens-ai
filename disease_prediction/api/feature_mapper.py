"""
MEDLENS — Central Feature Normalization & Model Mapping Layer
Maps extracted laboratory biomarkers to the exact feature schemas expected by validated production ML pipelines.
Provides explicit 3-state tracking:
  - STATE A (EXTRACTED): Feature available and valid
  - STATE B (UNCERTAIN): Feature present in report but mapping needs confirmation
  - STATE C (MISSING): Feature is genuinely absent from the report
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd


MODEL_FEATURE_REQUIREMENTS = {
    "anemia": {
        "name": "Anemia (CBC Panel)",
        "pipeline_file": "anemia_pipeline.joblib",
        "algorithm": "Logistic Regression",
        "features": [
            {"name": "Age", "type": "demographic", "key": "age", "label": "Age (Years)"},
            {"name": "Sex", "type": "demographic", "key": "gender", "label": "Sex / Gender"},
            {"name": "HGB", "type": "biomarker", "canonical": "HGB", "label": "Hemoglobin (HGB)", "unit": "g/dL"},
            {"name": "RBC", "type": "biomarker", "canonical": "RBC", "label": "Total RBC Count", "unit": "million/µL"},
            {"name": "PCV", "type": "biomarker", "canonical": "PCV", "label": "Packed Cell Volume (PCV)", "unit": "%"},
            {"name": "MCV", "type": "biomarker", "canonical": "MCV", "label": "Mean Corpuscular Volume (MCV)", "unit": "fL"},
            {"name": "MCH", "type": "biomarker", "canonical": "MCH", "label": "Mean Corpuscular Hemoglobin (MCH)", "unit": "pg"},
            {"name": "MCHC", "type": "biomarker", "canonical": "MCHC", "label": "MCHC", "unit": "g/dL"},
            {"name": "RDW", "type": "biomarker", "canonical": "RDW", "label": "Red Cell Distribution Width (RDW)", "unit": "%"},
            {"name": "TLC", "type": "biomarker", "canonical": "WBC", "label": "Total Leukocyte Count (TLC / WBC)", "unit": "/µL"},
            {"name": "PLT /mm3", "type": "biomarker", "canonical": "PLT", "label": "Platelet Count", "unit": "/mm3"}
        ]
    },
    "dengue": {
        "name": "Dengue Hematology Profile",
        "pipeline_file": "dengue_pipeline.joblib",
        "algorithm": "Random Forest Classifier",
        "features": [
            {"name": "age", "type": "demographic", "key": "age", "label": "Age (Years)"},
            {"name": "gender", "type": "demographic", "key": "gender", "label": "Gender"},
            {"name": "hemoglobin_g_dl", "type": "biomarker", "canonical": "HGB", "label": "Hemoglobin", "unit": "g/dL"},
            {"name": "wbc_count", "type": "biomarker", "canonical": "WBC", "label": "WBC Count", "unit": "cells/µL"},
            {"name": "differential_count", "type": "biomarker", "canonical": "DIFFERENTIAL_COUNT", "label": "Differential Count Flag", "default": 0},
            {"name": "rbc_count", "type": "biomarker", "canonical": "RBC", "label": "RBC Morphology Flag", "default": 1},
            {"name": "platelet_count", "type": "biomarker", "canonical": "PLT", "label": "Platelet Count", "unit": "cells/µL"},
            {"name": "platelet_distribution_width", "type": "biomarker", "canonical": "PDW", "label": "Platelet Distribution Width", "unit": "%"}
        ]
    },
    "liver": {
        "name": "Liver Function Test (LFT Panel)",
        "pipeline_file": "liver_pipeline.joblib",
        "algorithm": "Gradient Boosting Classifier",
        "features": [
            {"name": "age", "type": "demographic", "key": "age", "label": "Age (Years)"},
            {"name": "gender", "type": "demographic", "key": "gender", "label": "Gender"},
            {"name": "total_bilirubin", "type": "biomarker", "canonical": "TOTAL_BILIRUBIN", "label": "Total Bilirubin", "unit": "mg/dL"},
            {"name": "direct_bilirubin", "type": "biomarker", "canonical": "DIRECT_BILIRUBIN", "label": "Direct Bilirubin", "unit": "mg/dL"},
            {"name": "alkaline_phosphotase", "type": "biomarker", "canonical": "ALP", "label": "Alkaline Phosphatase (ALP)", "unit": "U/L"},
            {"name": "alamine_aminotransferase", "type": "biomarker", "canonical": "ALT", "label": "ALT / SGPT", "unit": "U/L"},
            {"name": "aspartate_aminotransferase", "type": "biomarker", "canonical": "AST", "label": "AST / SGOT", "unit": "U/L"},
            {"name": "total_protiens", "type": "biomarker", "canonical": "TOTAL_PROTEIN", "label": "Total Protein", "unit": "g/dL"},
            {"name": "albumin", "type": "biomarker", "canonical": "ALBUMIN", "label": "Albumin", "unit": "g/dL"},
            {"name": "albumin_and_globulin_ratio", "type": "biomarker", "canonical": "AG_RATIO", "label": "A/G Ratio", "unit": "ratio"}
        ]
    },
    "thyroid": {
        "name": "Thyroid Hormone Profile",
        "pipeline_file": "thyroid_pipeline.joblib",
        "algorithm": "Multinomial Logistic Regression",
        "features": [
            {"name": "TSH", "type": "biomarker", "canonical": "TSH", "label": "TSH", "unit": "µIU/mL"},
            {"name": "T4", "type": "biomarker", "canonical": "T4", "label": "Thyroxine (T4)", "unit": "µg/dL"},
            {"name": "T3", "type": "biomarker", "canonical": "T3", "label": "Triiodothyronine (T3)", "unit": "ng/dL"},
            {"name": "TSH_response", "type": "biomarker", "canonical": "TSH_RESPONSE", "label": "TSH Response to TRH", "unit": "ratio"},
            {"name": "T3_resin_uptake", "type": "biomarker", "canonical": "T3_RESIN_UPTAKE", "label": "T3 Resin Uptake", "unit": "%"}
        ]
    }
}


def build_canonical_parameter_lookup(parameters: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Builds a lookup index from extracted parameters by canonical_key, normalized_name, and alias."""
    lookup = {}
    for p in parameters:
        val = p.get("value")
        if val is None or val == "" or val == "Not extracted":
            continue

        c_key = str(p.get("canonical_key", "")).upper().strip()
        norm_name = str(p.get("normalized_name", "")).upper().strip()
        orig_name = str(p.get("original_name", "")).upper().strip()
        param_name = str(p.get("parameter", "")).upper().strip()

        p_obj = {
            "value": val,
            "unit": p.get("unit", ""),
            "confidence": p.get("confidence", "HIGH"),
            "status": p.get("status", "NORMAL"),
            "original_name": p.get("original_name", param_name),
            "canonical_key": c_key
        }

        if c_key:
            lookup[c_key] = p_obj
        if norm_name:
            lookup[norm_name] = p_obj
        if orig_name:
            lookup[orig_name] = p_obj
        if param_name:
            lookup[param_name] = p_obj

    return lookup


def map_features_for_model(
    model_key: str,
    parameters: List[Dict[str, Any]],
    patient_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Maps extracted report biomarkers to a model's exact expected dataframe schema with 3-state tracking.
    Enforces validation AFTER canonical aliases and units are normalized.
    """
    spec = MODEL_FEATURE_REQUIREMENTS.get(model_key)
    if not spec:
        return {"can_evaluate": False, "message": f"Unknown model key: {model_key}"}

    lookup = build_canonical_parameter_lookup(parameters)
    patient_meta = patient_meta or {}

    feature_states = {}
    feature_row = {}
    missing_features = []
    available_count = 0

    # Demographics
    raw_age = patient_meta.get("age")
    try:
        age_val = float(raw_age) if raw_age is not None else 30.0
    except (ValueError, TypeError):
        age_val = 30.0

    raw_gender = str(patient_meta.get("gender") or "Female").strip().capitalize()
    if not raw_gender or raw_gender not in ["Male", "Female", "Child"]:
        raw_gender = "Female"

    for feat in spec["features"]:
        feat_name = feat["name"]
        label = feat["label"]

        if feat["type"] == "demographic":
            if feat["key"] == "age":
                val = age_val
            else:
                val = raw_gender
            feature_row[feat_name] = val
            feature_states[feat_name] = {
                "state": "EXTRACTED",
                "value": val,
                "label": label,
                "source": "Patient Demographics"
            }
            available_count += 1
            continue

        # Biomarker feature mapping
        canon = feat.get("canonical", "")
        param_match = lookup.get(canon) or lookup.get(feat_name.upper())

        # Derived calculations if not directly available:
        # e.g., A/G ratio = albumin / (total_protein - albumin)
        if not param_match and feat_name == "albumin_and_globulin_ratio":
            alb_match = lookup.get("ALBUMIN")
            tp_match = lookup.get("TOTAL_PROTEIN")
            if alb_match and tp_match:
                try:
                    alb_v = float(alb_match["value"])
                    tp_v = float(tp_match["value"])
                    glob_v = tp_v - alb_v
                    if glob_v > 0:
                        derived_ag = round(alb_v / glob_v, 2)
                        param_match = {
                            "value": derived_ag,
                            "unit": "ratio",
                            "confidence": "HIGH",
                            "original_name": "Derived (Albumin / Globulin Ratio)",
                            "canonical_key": "AG_RATIO"
                        }
                except (ValueError, TypeError):
                    pass

        # TLC / WBC alias check
        if not param_match and canon == "WBC":
            param_match = lookup.get("WBC") or lookup.get("TLC") or lookup.get("WHITE BLOOD CELL COUNT") or lookup.get("TOTAL LEUKOCYTE COUNT")

        # T3 Resin Uptake alias check
        if not param_match and canon == "T3_RESIN_UPTAKE":
            param_match = lookup.get("T3_RESIN_UPTAKE") or lookup.get("T3_RESIN") or lookup.get("T3 UPTAKE")

        # Dengue Differential Count Flag Handling:
        # If report has "Differential Count = 100%" (NORMAL), map binary flag to 0 (normal differential)
        if feat_name == "differential_count":
            diff_match = lookup.get("DIFFERENTIAL_COUNT") or lookup.get("DIFF_COUNT")
            if diff_match:
                st = str(diff_match.get("status", "NORMAL")).upper()
                try:
                    num_v = float(diff_match["value"])
                    # Normal 100% total differential -> binary 0 (normal)
                    if st in ["NORMAL", ""] or (95.0 <= num_v <= 105.0 and "ABN" not in st and "HIGH" not in st and "LOW" not in st):
                        flag_val = 0
                    else:
                        flag_val = 1
                    param_match = {
                        "value": flag_val,
                        "unit": "flag",
                        "confidence": "HIGH",
                        "original_name": "Differential Count Flag",
                        "canonical_key": "DIFFERENTIAL_COUNT"
                    }
                except (ValueError, TypeError):
                    pass

        # Dengue RBC Morphology Flag Handling:
        # If report has RBC Count present, map to 1 (normal morphology) unless explicitly flagged abnormal
        if feat_name == "rbc_count":
            rbc_match = lookup.get("RBC") or lookup.get("TOTAL RBC COUNT") or lookup.get("RBC COUNT")
            if rbc_match:
                st = str(rbc_match.get("status", "NORMAL")).upper()
                flag_val = 0 if "ABN" in st else 1
                param_match = {
                    "value": flag_val,
                    "unit": "flag",
                    "confidence": "HIGH",
                    "original_name": "RBC Morphology Flag",
                    "canonical_key": "RBC"
                }

        # Dengue PDW check
        if feat_name == "platelet_distribution_width" and not param_match:
            param_match = lookup.get("PDW") or lookup.get("PLATELET_DISTRIBUTION_WIDTH")

        # Liver Model LFT Auto-Calculations and Aliases:
        if feat_name == "albumin_and_globulin_ratio" and not param_match:
            param_match = lookup.get("AG_RATIO") or lookup.get("A_G_RATIO") or lookup.get("A/G RATIO")
            if not param_match:
                alb_m = lookup.get("ALBUMIN")
                tp_m = lookup.get("TOTAL_PROTEIN") or lookup.get("TOTAL_PROTIENS") or lookup.get("TOTAL PROTEIN")
                glob_m = lookup.get("GLOBULIN")
                if alb_m and tp_m:
                    try:
                        alb_v = float(alb_m["value"])
                        tp_v = float(tp_m["value"])
                        glob_v = tp_v - alb_v
                        if glob_v > 0:
                            calc_ag = round(alb_v / glob_v, 2)
                            param_match = {
                                "value": calc_ag,
                                "unit": "ratio",
                                "confidence": "HIGH",
                                "original_name": "Calculated A/G Ratio",
                                "canonical_key": "AG_RATIO"
                            }
                    except (ValueError, TypeError):
                        pass
                elif alb_m and glob_m:
                    try:
                        alb_v = float(alb_m["value"])
                        glob_v = float(glob_m["value"])
                        if glob_v > 0:
                            calc_ag = round(alb_v / glob_v, 2)
                            param_match = {
                                "value": calc_ag,
                                "unit": "ratio",
                                "confidence": "HIGH",
                                "original_name": "Calculated A/G Ratio",
                                "canonical_key": "AG_RATIO"
                            }
                    except (ValueError, TypeError):
                        pass

        if feat_name == "total_protiens" and not param_match:
            param_match = lookup.get("TOTAL_PROTEIN") or lookup.get("TOTAL PROTEIN") or lookup.get("TOTAL_PROTIENS")

        if feat_name == "alkaline_phosphotase" and not param_match:
            param_match = lookup.get("ALP") or lookup.get("ALKALINE PHOSPHATASE") or lookup.get("ALKALINE_PHOSPHATASE")

        if feat_name == "alamine_aminotransferase" and not param_match:
            param_match = lookup.get("ALT") or lookup.get("SGPT") or lookup.get("ALAMINE_AMINOTRANSFERASE")

        if feat_name == "aspartate_aminotransferase" and not param_match:
            param_match = lookup.get("AST") or lookup.get("SGOT") or lookup.get("ASPARTATE_AMINOTRANSFERASE")

        if param_match:
            raw_val = param_match["value"]
            try:
                num_val = float(raw_val)
                # Scale conversion for Platelets
                # Anemia model expects PLT /mm3 in ~150 - 450 range (thousands / uL)
                if feat_name == "PLT /mm3" and num_val > 1000:
                    num_val = round(num_val / 1000.0, 1)

                # Dengue model expects platelet_count in full count ~150000 - 450000
                if feat_name == "platelet_count" and num_val < 1000:
                    num_val = int(num_val * 1000)

                # Dengue model expects wbc_count in full cells/uL ~4000 - 11000
                if feat_name == "wbc_count" and num_val < 100:
                    num_val = int(num_val * 1000)

                # Anemia model expects TLC in x10^3/uL ~4.0 - 11.0
                if feat_name == "TLC" and num_val > 100:
                    num_val = round(num_val / 1000.0, 2)

                feature_row[feat_name] = num_val
                feature_states[feat_name] = {
                    "state": "EXTRACTED",
                    "value": num_val,
                    "label": label,
                    "confidence": param_match.get("confidence", "HIGH")
                }
                available_count += 1
            except (ValueError, TypeError):
                feature_states[feat_name] = {
                    "state": "UNCERTAIN",
                    "value": raw_val,
                    "label": label
                }
                missing_features.append(label)
        else:
            feature_states[feat_name] = {
                "state": "MISSING",
                "value": None,
                "label": label
            }
            missing_features.append(label)

    total_required = len(spec["features"])
    can_evaluate = (len(missing_features) == 0)

    return {
        "model_key": model_key,
        "model_name": spec["name"],
        "pipeline_file": spec["pipeline_file"],
        "algorithm": spec["algorithm"],
        "total_required": total_required,
        "available_count": available_count,
        "missing_features": missing_features,
        "feature_states": feature_states,
        "feature_row": feature_row if can_evaluate else None,
        "can_evaluate": can_evaluate
    }
