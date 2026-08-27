"""
MEDLENS — ML Model Bridge with Central Feature Mapping & 3-State Tracking
Evaluates extracted report parameters against existing validated production pipelines:
- Anemia (Logistic Regression)
- Dengue (Random Forest)
- Liver Disease (Gradient Boosting)
- Thyroid Disorder (Multinomial Logistic Regression)
"""

import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

from disease_prediction.api.feature_mapper import map_features_for_model, MODEL_FEATURE_REQUIREMENTS


MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# Global lazy cache for validated production pipelines
_LOADED_MODELS: Dict[str, Any] = {}


def load_pipeline(name: str) -> Optional[Any]:
    """Lazy loads a validated production model pipeline from disk."""
    if name in _LOADED_MODELS:
        return _LOADED_MODELS[name]

    model_path = MODELS_DIR / f"{name}_pipeline.joblib"
    if not model_path.exists():
        return None

    try:
        loaded = joblib.load(model_path)
        if isinstance(loaded, dict) and "pipeline" in loaded:
            _LOADED_MODELS[name] = loaded["pipeline"]
        else:
            _LOADED_MODELS[name] = loaded
        return _LOADED_MODELS[name]
    except Exception as e:
        print(f"Error loading model pipeline {name}: {e}")
        return None


def _create_unevaluated_model_entry(model_map: Dict[str, Any], err_msg: Optional[str] = None) -> Dict[str, Any]:
    avail_cnt = model_map.get("available_count", 0)
    tot_req = model_map.get("total_required", 0)
    missing = model_map.get("missing_features", [])

    if err_msg:
        data_state = "ERROR"
        status = "PIPELINE ERROR"
        message = f"Execution error: {err_msg}"
        status_label = "Pipeline execution error"
    elif avail_cnt >= 3 or (tot_req > 0 and (avail_cnt / tot_req) >= 0.35):
        data_state = "PARTIAL"
        status = "PARTIAL DATA"
        status_label = f"{avail_cnt}/{tot_req} required features available"
        missing_preview = ", ".join(missing[:4])
        if len(missing) > 4:
            missing_preview += f" (+{len(missing)-4} more)"
        message = f"Partially extracted ({avail_cnt}/{tot_req} features). Missing: {missing_preview}."
    else:
        data_state = "INSUFFICIENT"
        status = "INSUFFICIENT DATA"
        status_label = f"Only {avail_cnt}/{tot_req} required features available"
        message = f"Too few panel features available ({avail_cnt}/{tot_req}) for reliable algorithmic inference."

    return {
        "evaluated": False,
        "data_state": data_state,
        "status": status,
        "status_label": status_label,
        "disease": model_map["model_name"],
        "model_used": f"{model_map['algorithm']} ({model_map['pipeline_file']})",
        "message": message,
        "total_required": tot_req,
        "available_count": avail_cnt,
        "missing_features": missing,
        "feature_states": model_map.get("feature_states", {})
    }


def evaluate_extracted_report_with_ml(
    parameters: List[Dict[str, Any]], 
    patient_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates structured laboratory parameters against all compatible existing ML pipelines.
    Uses centralized feature mapping, transparent 3-state tracking (AVAILABLE / PARTIAL / INSUFFICIENT),
    and never fabricates values.
    """
    results = {}

    # -------------------------------------------------------------
    # 1. Anemia Pipeline (Logistic Regression)
    # -------------------------------------------------------------
    anemia_map = map_features_for_model("anemia", parameters, patient_meta)
    anemia_pipe = load_pipeline("anemia")
    if anemia_pipe:
        if anemia_map["can_evaluate"]:
            try:
                df_in = pd.DataFrame([anemia_map["feature_row"]])
                pred_code = int(anemia_pipe.predict(df_in)[0])
                proba = float(np.max(anemia_pipe.predict_proba(df_in)[0])) if hasattr(anemia_pipe, "predict_proba") else 1.0
                pred_label = "Anemic" if pred_code == 1 else "Normal"
                results["anemia"] = {
                    "evaluated": True,
                    "data_state": "AVAILABLE",
                    "status": "MODEL ANALYSIS AVAILABLE",
                    "status_label": f"{anemia_map['available_count']}/{anemia_map['total_required']} required features available",
                    "disease": anemia_map["model_name"],
                    "model_used": f"{anemia_map['algorithm']} ({anemia_map['pipeline_file']})",
                    "prediction": pred_label,
                    "confidence": round(proba, 4),
                    "confidence_pct": round(proba * 100, 1),
                    "risk_level": "High" if pred_code == 1 else "Low",
                    "total_required": anemia_map["total_required"],
                    "available_count": anemia_map["available_count"],
                    "missing_features": anemia_map["missing_features"],
                    "feature_states": anemia_map["feature_states"]
                }
            except Exception as e:
                results["anemia"] = _create_unevaluated_model_entry(anemia_map, err_msg=str(e))
        else:
            results["anemia"] = _create_unevaluated_model_entry(anemia_map)

    # -------------------------------------------------------------
    # 2. Dengue Pipeline (Random Forest)
    # -------------------------------------------------------------
    dengue_map = map_features_for_model("dengue", parameters, patient_meta)
    dengue_pipe = load_pipeline("dengue")
    if dengue_pipe:
        if dengue_map["can_evaluate"]:
            try:
                df_in = pd.DataFrame([dengue_map["feature_row"]])
                pred_code = int(dengue_pipe.predict(df_in)[0])
                proba = float(np.max(dengue_pipe.predict_proba(df_in)[0])) if hasattr(dengue_pipe, "predict_proba") else 1.0
                pred_label = "Positive" if pred_code == 1 else "Negative"
                results["dengue"] = {
                    "evaluated": True,
                    "data_state": "AVAILABLE",
                    "status": "MODEL ANALYSIS AVAILABLE",
                    "status_label": f"{dengue_map['available_count']}/{dengue_map['total_required']} required features available",
                    "disease": dengue_map["model_name"],
                    "model_used": f"{dengue_map['algorithm']} ({dengue_map['pipeline_file']})",
                    "prediction": pred_label,
                    "confidence": round(proba, 4),
                    "confidence_pct": round(proba * 100, 1),
                    "risk_level": "High" if pred_code == 1 else "Low",
                    "total_required": dengue_map["total_required"],
                    "available_count": dengue_map["available_count"],
                    "missing_features": dengue_map["missing_features"],
                    "feature_states": dengue_map["feature_states"]
                }
            except Exception as e:
                results["dengue"] = _create_unevaluated_model_entry(dengue_map, err_msg=str(e))
        else:
            results["dengue"] = _create_unevaluated_model_entry(dengue_map)

    # -------------------------------------------------------------
    # 3. Liver Disease Pipeline (Gradient Boosting)
    # -------------------------------------------------------------
    liver_map = map_features_for_model("liver", parameters, patient_meta)
    liver_pipe = load_pipeline("liver")
    if liver_pipe:
        if liver_map["can_evaluate"]:
            try:
                df_in = pd.DataFrame([liver_map["feature_row"]])
                pred_code = int(liver_pipe.predict(df_in)[0])
                proba = float(np.max(liver_pipe.predict_proba(df_in)[0])) if hasattr(liver_pipe, "predict_proba") else 1.0
                pred_label = "Liver Disease Pattern" if pred_code == 1 else "Normal Liver Panel"
                results["liver"] = {
                    "evaluated": True,
                    "data_state": "AVAILABLE",
                    "status": "MODEL ANALYSIS AVAILABLE",
                    "status_label": f"{liver_map['available_count']}/{liver_map['total_required']} required features available",
                    "disease": liver_map["model_name"],
                    "model_used": f"{liver_map['algorithm']} ({liver_map['pipeline_file']})",
                    "prediction": pred_label,
                    "confidence": round(proba, 4),
                    "confidence_pct": round(proba * 100, 1),
                    "risk_level": "High" if pred_code == 1 else "Low",
                    "total_required": liver_map["total_required"],
                    "available_count": liver_map["available_count"],
                    "missing_features": liver_map["missing_features"],
                    "feature_states": liver_map["feature_states"]
                }
            except Exception as e:
                results["liver"] = _create_unevaluated_model_entry(liver_map, err_msg=str(e))
        else:
            results["liver"] = _create_unevaluated_model_entry(liver_map)

    # -------------------------------------------------------------
    # 4. Thyroid Pipeline (Multinomial Logistic Regression)
    # -------------------------------------------------------------
    thyroid_map = map_features_for_model("thyroid", parameters, patient_meta)
    thyroid_pipe = load_pipeline("thyroid")
    if thyroid_pipe:
        if thyroid_map["can_evaluate"]:
            try:
                df_in = pd.DataFrame([thyroid_map["feature_row"]])
                pred_code = int(thyroid_pipe.predict(df_in)[0])
                target_mapping = {1: "Normal", 2: "Hyperthyroid", 3: "Hypothyroid"}
                pred_label = target_mapping.get(pred_code, f"Class {pred_code}")
                proba = float(np.max(thyroid_pipe.predict_proba(df_in)[0])) if hasattr(thyroid_pipe, "predict_proba") else 1.0
                results["thyroid"] = {
                    "evaluated": True,
                    "data_state": "AVAILABLE",
                    "status": "MODEL ANALYSIS AVAILABLE",
                    "status_label": f"{thyroid_map['available_count']}/{thyroid_map['total_required']} required features available",
                    "disease": thyroid_map["model_name"],
                    "model_used": f"{thyroid_map['algorithm']} ({thyroid_map['pipeline_file']})",
                    "prediction": pred_label,
                    "confidence": round(proba, 4),
                    "confidence_pct": round(proba * 100, 1),
                    "risk_level": "High" if pred_code != 1 else "Low",
                    "total_required": thyroid_map["total_required"],
                    "available_count": thyroid_map["available_count"],
                    "missing_features": thyroid_map["missing_features"],
                    "feature_states": thyroid_map["feature_states"]
                }
            except Exception as e:
                results["thyroid"] = _create_unevaluated_model_entry(thyroid_map, err_msg=str(e))
        else:
            results["thyroid"] = _create_unevaluated_model_entry(thyroid_map)

    return results
