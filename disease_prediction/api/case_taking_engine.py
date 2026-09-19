"""
MEDLENS AI x Medicover — Clinical Case-Taking Intelligence Engine
Provides:
- 10 Structured Clinical History Section Schemas
- Adaptive Clinical Question Tree & Follow-up Generator
- Red Flag Emergency & Triage Detection
- Optional AYUSH Prakriti & Clinical Profile Evaluation
- Physician-Ready Structured Case Summary Synthesis
"""

import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# ==============================================================================
# 10 STRUCTURED CLINICAL SECTIONS
# ==============================================================================
CLINICAL_SECTIONS = [
    {
        "id": "chief_complaint",
        "title": "Chief Complaint",
        "icon": "chat_bubble",
        "description": "Primary symptom or reason for seeking medical consultation and its duration.",
        "placeholder": "e.g. Sharp chest pain for 2 days, high fever with chills since yesterday...",
        "chips": ["Chest Pain", "Shortness of Breath", "High Fever", "Severe Headache", "Abdominal Pain", "Joint Pain", "Cough & Cold", "Dizziness"]
    },
    {
        "id": "hpi",
        "title": "History of Present Illness (HPI)",
        "icon": "timeline",
        "description": "Onset, character, location, radiation, severity (1-10), aggravating and relieving factors.",
        "placeholder": "Describe how the symptom started, whether it spreads, what makes it better or worse...",
        "chips": ["Gradual onset", "Sudden onset", "Continuous", "Intermittent", "Radiating to left arm/jaw", "Aggravated by exertion", "Relieved by rest"]
    },
    {
        "id": "past_medical",
        "title": "Past Medical History",
        "icon": "history",
        "description": "Pre-existing chronic conditions, previous hospitalizations, or long-term illnesses.",
        "placeholder": "e.g. Hypertension (5 yrs), Type 2 Diabetes (3 yrs), Asthma since childhood...",
        "chips": ["Hypertension", "Diabetes Mellitus", "Asthma / COPD", "Coronary Artery Disease", "Thyroid Disorder", "Kidney Disease", "None / No Known Conditions"]
    },
    {
        "id": "past_surgical",
        "title": "Past Surgical History",
        "icon": "medical_services",
        "description": "Previous surgeries, procedures, dates, and any anesthesia complications.",
        "placeholder": "e.g. Appendectomy (2020), Cesarean Section (2018), Knee Arthroscopy...",
        "chips": ["Appendectomy", "Cholecystectomy", "Cesarean Section", "Hernia Repair", "Cardiac Stenting", "No Prior Surgeries"]
    },
    {
        "id": "drug_history",
        "title": "Drug History & Medications",
        "icon": "medication",
        "description": "Current prescription medications, over-the-counter drugs, dosages, and compliance.",
        "placeholder": "e.g. Tab Metformin 500mg BD, Tab Telmisartan 40mg OD, Aspirin 75mg...",
        "chips": ["Metformin 500mg", "Telmisartan 40mg", "Amlodipine 5mg", "Atorvastatin 10mg", "Thyroxine 50mcg", "Not Taking Any Medications"]
    },
    {
        "id": "allergy_history",
        "title": "Allergy History",
        "icon": "warning",
        "description": "Known allergies to drugs, antibiotics, foods, latex, or IV contrast dye.",
        "placeholder": "e.g. Severe rash with Penicillin, Sulfa allergy, Peanut allergy...",
        "chips": ["Penicillin Allergy", "Sulfa Drugs", "NSAIDs / Aspirin", "Contrast Dye", "Food Allergies", "No Known Drug Allergies (NKDA)"]
    },
    {
        "id": "family_history",
        "title": "Family History",
        "icon": "family_restroom",
        "description": "Hereditary or familial conditions in parents, siblings, or grandparents.",
        "placeholder": "e.g. Father had MI at age 52, Mother has Type 2 Diabetes and Hypertension...",
        "chips": ["Early Heart Disease / MI", "Diabetes", "Hypertension", "Cancer History", "Asthma / Allergies", "No Significant Family History"]
    },
    {
        "id": "personal_history",
        "title": "Personal & Social History",
        "icon": "person",
        "description": "Dietary habits, smoking, alcohol, sleep patterns, physical activity, and occupation.",
        "placeholder": "e.g. Non-smoker, occasional alcohol, vegetarian diet, desk job, 6 hrs sleep...",
        "chips": ["Non-Smoker", "Ex-Smoker", "Smoker", "Non-Drinker", "Vegetarian", "Non-Vegetarian", "Sedentary", "Active"]
    },
    {
        "id": "ros",
        "title": "Review of Systems (ROS)",
        "icon": "checklist",
        "description": "Systemic screening (Cardiovascular, Respiratory, Gastrointestinal, Neurological, Musculoskeletal).",
        "placeholder": "e.g. No palpitations, occasional cough, normal appetite, no bowel changes, no limb weakness...",
        "chips": ["No Palpitations", "No Shortness of Breath", "Normal Appetite & Bowel", "No Joint Swelling", "No Blurry Vision / Headaches"]
    },
    {
        "id": "previous_investigations",
        "title": "Previous Investigations",
        "icon": "biotech",
        "description": "Prior laboratory reports, imaging (X-Ray, CT, MRI, ECG), biopsy, or pathology tests.",
        "placeholder": "e.g. ECG normal last month, CBC showed Hb 10.5 g/dL, Ultrasound abdomen normal...",
        "chips": ["Recent Normal ECG", "Prior Low Hemoglobin", "Elevated Liver Enzymes", "Thyroid Ultrasound Done", "No Prior Investigations Available"]
    }
]


# ==============================================================================
# RED FLAG & TRIAGE DETECTION RULES
# ==============================================================================
RED_FLAG_PATTERNS = [
    {
        "id": "ACUTE_CORONARY_SYNDROME",
        "regex": r"(chest\s*pain|crushing|tightness|heaviness|pressure)\s*.*(radiat|spread|arm|left\s*shoulder|jaw|sweat|diaphoresis|breath)",
        "message": "POTENTIAL CARDIAC EMERGENCY: Severe chest discomfort radiating to left arm/jaw or accompanied by shortness of breath/sweating.",
        "level": "emergency"
    },
    {
        "id": "ACUTE_DYSPNEA",
        "regex": r"(gasping|severe\s*breathless|cannot\s*breathe|stridor|choking|cyanosis|blue\s*lips|unable\s*to\s*speak)",
        "message": "RESPIRATORY DISTRESS: Severe difficulty breathing or respiratory compromise.",
        "level": "emergency"
    },
    {
        "id": "ACUTE_STROKE",
        "regex": r"(sudden\s*(weakness|numbness|paralysis)|facial\s*droop|slurred\s*speech|loss\s*of\s*speech|hemiplegia)",
        "message": "POTENTIAL STROKE ALERT: Sudden neurological deficit, facial asymmetry, or speech difficulty.",
        "level": "emergency"
    },
    {
        "id": "ALTERED_CONSCIOUSNESS",
        "regex": r"(loss\s*of\s*consciousness|fainted|syncope|unresponsive|blackout|seizure|convulsion)",
        "message": "NEUROLOGICAL EMERGENCY: Unresponsiveness, loss of consciousness, or seizure activity.",
        "level": "emergency"
    },
    {
        "id": "SEVERE_HEMORRHAGE",
        "regex": r"(vomit\s*blood|hematemesis|cough\s*blood|hemoptysis|black\s*stool|melena|severe\s*bleed|profuse\s*bleeding)",
        "message": "ACUTE HEMORRHAGE ALERT: Signs of active internal or significant external bleeding.",
        "level": "emergency"
    },
    {
        "id": "ANAPHYLAXIS",
        "regex": r"(throat\s*swelling|tongue\s*swelling|hives.*breath|anaphylaxis|swollen\s*airway)",
        "message": "SEVERE ALLERGIC REACTION: Possible airway involvement or anaphylaxis.",
        "level": "emergency"
    },
    {
        "id": "HIGH_FEVER_RIGORS",
        "regex": r"(high\s*fever|104|rigors|stiff\s*neck|photophobia)",
        "message": "HIGH-RISK INFECTION: High fever with severe systemic features or meningism signs.",
        "level": "priority"
    }
]

def detect_red_flags(combined_text: str) -> Dict[str, Any]:
    """Scans all patient statements and history records for clinical triage red flags."""
    text = combined_text.lower()
    flags = []
    highest_level = "routine"

    for rule in RED_FLAG_PATTERNS:
        if re.search(rule["regex"], text, re.IGNORECASE):
            flags.append({
                "rule_id": rule["id"],
                "message": rule["message"],
                "level": rule["level"]
            })
            if rule["level"] == "emergency":
                highest_level = "emergency"
            elif rule["level"] == "priority" and highest_level != "emergency":
                highest_level = "priority"

    return {
        "has_red_flags": len(flags) > 0,
        "triage_level": highest_level,
        "flags": flags,
        "warning_banner": flags[0]["message"] if flags else None
    }


# ==============================================================================
# ADAPTIVE QUESTION ENGINE (Deterministic + Clinical Intelligence)
# ==============================================================================
ADAPTIVE_RULES = [
    {
        "trigger": r"chest\s*pain|angina|cardiac",
        "section": "hpi",
        "questions": [
            {
                "id": "cp_onset",
                "question": "When exactly did the chest pain start, and was it sudden or gradual?",
                "options": ["Sudden onset (< 1 hour)", "Started earlier today", "Present for 2-3 days", "Chronic / on and off for weeks"]
            },
            {
                "id": "cp_radiation",
                "question": "Does the pain spread or radiate anywhere else (e.g., left arm, shoulder, neck, jaw, or back)?",
                "options": ["Spreads to left arm & shoulder", "Spreads to jaw / neck", "Spreads to upper back", "Remains localized in the center"]
            },
            {
                "id": "cp_character",
                "question": "How would you describe the feeling of the pain?",
                "options": ["Crushing / heavy pressure", "Sharp / stabbing like a needle", "Burning sensation", "Dull ache"]
            },
            {
                "id": "cp_triggers",
                "question": "Does walking, climbing stairs, or physical exertion worsen the chest pain?",
                "options": ["Yes, exertion definitely worsens it", "No, happens even at rest", "Worse when lying flat / after meals", "Worse with deep breaths / coughing"]
            }
        ]
    },
    {
        "trigger": r"fever|pyrexia|temperature|chills",
        "section": "hpi",
        "questions": [
            {
                "id": "fever_duration",
                "question": "How many days have you had the fever, and what was the highest recorded temperature?",
                "options": ["1-2 days (Low grade < 100°F)", "3-5 days (High grade > 102°F)", "> 1 week continuous", "Intermittent with severe chills & rigors"]
            },
            {
                "id": "fever_associated",
                "question": "Are you experiencing any associated symptoms along with the fever?",
                "options": ["Severe headache & body ache", "Cough & sore throat", "Burning urination / flank pain", "Nausea, vomiting & abdominal pain", "Skin rash or red spots"]
            }
        ]
    },
    {
        "trigger": r"breath|dyspnea|shortness\s*of\s*breath|wheez",
        "section": "hpi",
        "questions": [
            {
                "id": "dyspnea_severity",
                "question": "When is the shortness of breath most noticeable?",
                "options": ["At rest / sitting still", "With mild activity (walking across room)", "With moderate exertion (climbing stairs)", "When lying flat at night (need extra pillows)"]
            },
            {
                "id": "dyspnea_cough",
                "question": "Do you have a cough, wheezing, or phlegm?",
                "options": ["Dry cough only", "Productive cough with yellow/green phlegm", "Wheezing / whistling sound", "No cough"]
            }
        ]
    },
    {
        "trigger": r"abdom|stomach\s*pain|belly|nausea|vomit|diarrhea",
        "section": "hpi",
        "questions": [
            {
                "id": "abd_location",
                "question": "Where in your abdomen is the pain located?",
                "options": ["Upper center (epigastric)", "Right upper side (under ribs)", "Right lower abdomen", "Diffuse / all over"]
            },
            {
                "id": "abd_relation_food",
                "question": "Is the pain related to eating or taking spicy/greasy meals?",
                "options": ["Worse immediately after meals", "Better after eating", "Unrelated to food", "Accompanied by vomiting / loose stools"]
            }
        ]
    },
    {
        "trigger": r"headache|migraine|head\s*pain",
        "section": "hpi",
        "questions": [
            {
                "id": "ha_character",
                "question": "Is the headache throbbing on one side or a dull band across the entire forehead?",
                "options": ["One-sided pulsating / throbbing", "Tight band around head", "Sudden severe 'thunderclap' headache", "Back of head / neck stiffness"]
            },
            {
                "id": "ha_vision",
                "question": "Do you experience sensitivity to light/sound or nausea during the headache?",
                "options": ["Yes, light sensitivity & nausea", "Visual blurring or seeing flashing lights", "No associated symptoms"]
            }
        ]
    }
]

def get_deterministic_adaptive_questions(chief_complaint: str, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    User's built-in deterministic clinical rule engine:
    Evaluates chief complaint and current section answers using predefined clinical rules.
    """
    combined = f"{chief_complaint} " + " ".join([str(v) for v in answers.values()])
    suggested = []
    
    for rule in ADAPTIVE_RULES:
        if re.search(rule["trigger"], combined, re.IGNORECASE):
            for q in rule["questions"]:
                if q["id"] not in answers:
                    suggested.append(q)
    
    # Fallback questions if no specialized match
    if not suggested:
        suggested = [
            {
                "id": "gen_onset",
                "question": "When did these symptoms first begin, and have they changed over time?",
                "options": ["Started today", "Past 2-3 days", "1-2 weeks ago", "Long-standing issue (> 1 month)"]
            },
            {
                "id": "gen_severity",
                "question": "On a scale of 1 to 10, how severe is your discomfort right now?",
                "options": ["Mild (1 - 3)", "Moderate (4 - 6)", "Severe (7 - 8)", "Very Severe (9 - 10)"]
            }
        ]
    
    return suggested[:3]


def get_ai_adaptive_questions(chief_complaint: str, answers: Dict[str, Any], timeout: float = 2.5) -> Optional[List[Dict[str, Any]]]:
    """
    Calls OpenRouter AI API to generate tailored clinical follow-up questions.
    Returns None if API key is missing, network fails, times out, or output is invalid.
    """
    if not chief_complaint or not chief_complaint.strip():
        return None

    try:
        try:
            from disease_prediction.api.openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME
        except ImportError:
            from openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME
        import requests
    except Exception:
        return None

    api_key = get_api_key()
    if not api_key:
        return None

    prompt = (
        "You are an expert clinical history intake assistant for an outpatient clinic.\n"
        "Generate 2 to 3 clinically relevant follow-up questions based on the patient's complaint and recorded answers.\n"
        "Follow standard clinical history protocol (OPQRST / SOCRATES).\n"
        "CRITICAL RULES:\n"
        "1. DO NOT provide a diagnosis, medical advice, or reassure the patient.\n"
        "2. Only ask intake questions to gather more specific clinical history.\n"
        "3. For each question, provide 3 to 4 concise selectable options / answer chips.\n"
        f"Chief Complaint: {chief_complaint}\n"
        f"Known Answers: {json.dumps(answers)}\n\n"
        "Respond ONLY with a JSON array in this exact format:\n"
        "[\n"
        '  {"id": "q1", "question": "Question text here?", "options": ["Option 1", "Option 2", "Option 3"]},\n'
        '  {"id": "q2", "question": "Question text here?", "options": ["Option 1", "Option 2", "Option 3"]}\n'
        "]"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": SITE_URL,
        "X-Title": APP_NAME,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemma-4-31b-it:free",
        "messages": [
            {"role": "system", "content": "You are a clinical intake question generator. You only return valid JSON arrays."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 400
    }

    try:
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=(1.5, timeout))
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            match = re.search(r'(\[[\s\S]*\])', content)
            if match:
                raw_json = match.group(1)
                parsed = json.loads(raw_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    valid_qs = []
                    for i, q in enumerate(parsed[:3]):
                        if isinstance(q, dict) and "question" in q:
                            valid_qs.append({
                                "id": str(q.get("id") or f"ai_q_{i+1}"),
                                "question": str(q["question"]),
                                "options": [str(opt) for opt in q.get("options", []) if str(opt).strip()][:4],
                                "source": "ai_generated"
                            })
                    if valid_qs:
                        return valid_qs
    except Exception:
        # If API drops, times out, or fails, gracefully return None so built-in engine is used
        pass

    return None


def get_adaptive_questions(chief_complaint: str, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates chief complaint and current section answers.
    1. First attempts to query AI API for tailored follow-up questions.
    2. SAFETY FALLBACK: If the API key is missing, internet drops, or API gets stuck/times out,
       it seamlessly uses the user's built-in clinical engine so the screen never gets stuck.
    """
    ai_questions = get_ai_adaptive_questions(chief_complaint, answers, timeout=2.5)
    if ai_questions:
        return ai_questions

    # Built-in Engine Fallback
    return get_deterministic_adaptive_questions(chief_complaint, answers)


# ==============================================================================
# OPTIONAL AYUSH EVALUATION ENGINE
# ==============================================================================
AYUSH_FIELDS = [
    {
        "id": "prakriti",
        "title": "Prakriti (Constitutional Type)",
        "options": ["Vata Dominant (Lean, active, dry skin)", "Pitta Dominant (Medium build, warm, sharp digestion)", "Kapha Dominant (Solid build, calm, slow digestion)", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridoshic (Balanced)"]
    },
    {
        "id": "agni_ahara",
        "title": "Agni & Ahara Shakti (Digestive & Metabolic Capacity)",
        "options": ["Sama Agni (Balanced appetite & digestion)", "Tikshna Agni (Intense/excessive hunger, hyperacidity)", "Manda Agni (Sluggish digestion, heaviness)", "Visham Agni (Irregular/unpredictable appetite)"]
    },
    {
        "id": "vyayama_shakti",
        "title": "Vyayama Shakti (Physical Endurance & Exercise Capacity)",
        "options": ["Uttama (High physical stamina)", "Madhyama (Moderate stamina)", "Avara (Low stamina / easily fatigued)"]
    },
    {
        "id": "sattva",
        "title": "Sattva (Mental Temperament & Stress Tolerance)",
        "options": ["Pravara (High mental resilience & calm)", "Madhyama (Moderate stress tolerance)", "Avara (High anxiety, easily overwhelmed)"]
    },
    {
        "id": "ahara_vihara",
        "title": "Ahara & Vihara Patterns (Diet & Lifestyle)",
        "placeholder": "e.g. Irregular meal timings, late night sleep, high intake of dry/spicy food, sedentary routine..."
    }
]

def format_ayush_profile(ayush_data: Dict[str, Any]) -> Dict[str, Any]:
    """Structures optional AYUSH clinical parameters if provided by the patient."""
    if not ayush_data:
        return {"has_ayush": False, "details": "No AYUSH constitutional data recorded."}
    
    return {
        "has_ayush": True,
        "prakriti": ayush_data.get("prakriti", "Unspecified"),
        "agni_ahara": ayush_data.get("agni_ahara", "Unspecified"),
        "vyayama_shakti": ayush_data.get("vyayama_shakti", "Unspecified"),
        "sattva": ayush_data.get("sattva", "Unspecified"),
        "ahara_vihara": ayush_data.get("ahara_vihara", "Standard routine")
    }


# ==============================================================================
# PHYSICIAN-READY STRUCTURED CASE SUMMARY SYNTHESIZER
# ==============================================================================
def synthesize_physician_summary(
    patient_info: Dict[str, Any],
    case_info: Dict[str, Any],
    sections: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    ayush_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compiles patient interview, linked documents, and extracted findings
    into a structured, physician-ready Clinical Case Summary.
    """
    sec_map = {s["section_id"]: s for s in sections}
    
    # Extract sections with fallback
    def get_sec_text(sid: str, default: str = "None reported") -> str:
        s = sec_map.get(sid)
        if not s:
            return default
        raw = s.get("raw_input", "").strip()
        struct = s.get("structured_data", {})
        if raw:
            return raw
        if struct and isinstance(struct, dict):
            return ", ".join([f"{k}: {v}" for k, v in struct.items() if v])
        return default

    chief_complaint = case_info.get("chief_complaint") or get_sec_text("chief_complaint", "General medical review")
    hpi = get_sec_text("hpi", "No acute progression details provided.")
    past_medical = get_sec_text("past_medical", "No pre-existing chronic conditions noted.")
    past_surgical = get_sec_text("past_surgical", "No past surgical history reported.")
    drug_history = get_sec_text("drug_history", "No current medications documented.")
    allergy_history = get_sec_text("allergy_history", "No Known Drug Allergies (NKDA).")
    family_history = get_sec_text("family_history", "Non-contributory.")
    personal_history = get_sec_text("personal_history", "Standard diet, non-smoker, non-alcoholic.")
    ros = get_sec_text("ros", "Systemic review non-contributory.")
    prev_investigations = get_sec_text("previous_investigations", "No prior investigation records provided.")

    # Combine all text for red flag scanning
    all_text = f"{chief_complaint} {hpi} {past_medical} {drug_history} {ros}"
    red_flag_res = detect_red_flags(all_text)

    # Document findings aggregation
    attached_docs_summary = []
    for doc in documents:
        fname = doc.get("filename", "Attached Document")
        dtype = doc.get("document_type", "Lab Report")
        ext_data = doc.get("extracted_data", {})
        
        extracted_findings = []
        if isinstance(ext_data, list):
            for item in ext_data:
                param = item.get("parameter") or item.get("test_name") or item.get("name")
                val = item.get("value")
                unit = item.get("unit", "")
                flag = item.get("flag")
                if param and val is not None:
                    flag_str = f" [{flag}]" if flag and flag != "Normal" else ""
                    extracted_findings.append(f"{param}: {val} {unit}{flag_str}".strip())
        elif isinstance(ext_data, dict):
            for k, v in ext_data.items():
                if isinstance(v, dict):
                    extracted_findings.append(f"{k}: {v.get('value')} {v.get('unit', '')}".strip())
                elif v:
                    extracted_findings.append(f"{k}: {v}")

        attached_docs_summary.append({
            "filename": fname,
            "type": dtype,
            "key_parameters": extracted_findings[:8]
        })

    # Optional AYUSH formatting
    ayush_summary = format_ayush_profile(ayush_data or case_info.get("ayush_data", {}))

    summary_payload = {
        "header": {
            "title": "PATIENT CLINICAL CASE SHEET",
            "hospital": "MEDLENS AI x Medicover Clinical Diagnostic Platform",
            "generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "case_id": case_info.get("case_id"),
            "patient_id": patient_info.get("patient_id", case_info.get("patient_id")),
            "patient_name": patient_info.get("name", "Outpatient"),
            "age_gender": f"{patient_info.get('age', '—')} Yrs / {patient_info.get('gender', '—')}",
            "contact": patient_info.get("contact", "—"),
            "abha_id": case_info.get("abha_id") or "Not Registered (Demo)",
            "triage_urgency": red_flag_res["triage_level"].upper()
        },
        "red_flags": red_flag_res["flags"],
        "triage_level": red_flag_res["triage_level"],
        "sections": {
            "chief_complaint": chief_complaint,
            "hpi": hpi,
            "past_medical": past_medical,
            "past_surgical": past_surgical,
            "drug_history": drug_history,
            "allergy_history": allergy_history,
            "family_history": family_history,
            "personal_history": personal_history,
            "ros": ros,
            "previous_investigations": prev_investigations
        },
        "attached_documents": attached_docs_summary,
        "ayush_profile": ayush_summary,
        "disclaimer": (
            "DRAFT CLINICAL CASE SHEET: Generated from patient self-recorded history, voice inputs, "
            "and attached documents for clinical decision-support. Must be reviewed, verified, "
            "and confirmed by the attending physician before finalizing diagnosis."
        )
    }

    return summary_payload
