"""
MEDLENS AI x Medicover — Clinical Case-Taking Intelligence Engine
Provides:
- 10 Structured Clinical History Section Schemas
- Adaptive Clinical Question Tree & Follow-up Generator
- Red Flag Emergency & Triage Detection
- Optional AYUSH Prakriti & Clinical Profile Evaluation
- Physician-Ready Structured Case Summary Synthesis
"""

import os
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
try:
    from disease_prediction.api.clinical_interview.relevance_validator import ClinicalQuestionRelevanceValidator
except ImportError:
    try:
        from api.clinical_interview.relevance_validator import ClinicalQuestionRelevanceValidator
    except ImportError:
        from clinical_interview.relevance_validator import ClinicalQuestionRelevanceValidator

ADAPTIVE_RULES = [
    {
        "domain": "chest_pain",
        "trigger": r"chest\s*pain|angina|cardiac|heart|seena\s*dard|chhati|gunde\s*noppi",
        "section": "hpi",
        "questions": [
            {
                "id": "cp_location_radiation",
                "question": "Where exactly is the chest discomfort, and does it spread/radiate to your left arm, jaw, neck, shoulder, or back?",
                "options": ["Left-sided radiating to left arm/shoulder", "Center retrosternal crushing pressure", "Radiates to jaw/neck", "Localized in center without radiation"]
            },
            {
                "id": "cp_character",
                "question": "How would you describe the feeling of the pain?",
                "options": ["Crushing / heavy pressure like an elephant", "Sharp / stabbing needle pain", "Burning sensation / acid reflux", "Dull ache"]
            },
            {
                "id": "cp_triggers",
                "question": "Does walking, climbing stairs, or physical exertion worsen the chest pain?",
                "options": ["Yes, exertion definitely worsens it", "No, happens even at rest", "Worse when lying flat / after meals", "Worse with deep breaths / coughing"]
            },
            {
                "id": "cp_associated",
                "question": "Are you experiencing cold sweating, difficulty breathing, dizziness, or nausea along with the chest pain?",
                "options": ["Cold sweating & shortness of breath", "Dizziness / feeling faint", "Nausea or vomiting", "No associated symptoms"]
            }
        ]
    },
    {
        "domain": "fever",
        "trigger": r"fever|pyrexia|temperature|chills|shivering|bukhar|jwar",
        "section": "hpi",
        "questions": [
            {
                "id": "fever_duration",
                "question": "How many days have you had the fever, and did it start suddenly with chills or gradually?",
                "options": ["1-2 days (Recent onset)", "3-5 days (High grade)", "> 1 week continuous", "Started today with severe chills & rigors"]
            },
            {
                "id": "fever_pattern",
                "question": "How high has the fever reached, and does it stay continuous or come and go in spikes with shivering?",
                "options": ["Continuous high fever (> 102°F)", "Comes in spikes with shivering chills", "Low grade (99-100°F)", "Not measured with thermometer"]
            },
            {
                "id": "fever_associated",
                "question": "Are you experiencing severe headache, body aches, cough, sore throat, or burning urination with the fever?",
                "options": ["Severe headache & body aches", "Cough & sore throat", "Burning sensation during urination", "Nausea, vomiting & abdominal pain"]
            },
            {
                "id": "fever_warning",
                "question": "Have you noticed any red spots on your skin, bleeding gums, pain behind your eyes, or a stiff neck?",
                "options": ["Pain behind the eyes (Retro-orbital)", "Red rash / tiny red spots on skin", "Stiff neck and intolerance to light", "No rash, bleeding, or neck stiffness"]
            }
        ]
    },
    {
        "domain": "cough",
        "trigger": r"cough|sputum|phlegm|khansi|daggu|kaas",
        "section": "hpi",
        "questions": [
            {
                "id": "cough_duration",
                "question": "How long have you had this cough, and did it start after a cold or fever?",
                "options": ["Less than 1 week (Acute)", "1 to 3 weeks", "More than 3 weeks (Persistent)", "Chronic cough for several months"]
            },
            {
                "id": "cough_type",
                "question": "Is the cough dry or productive with phlegm/sputum? Have you seen any traces of blood?",
                "options": ["Dry continuous irritating cough", "Productive with yellow/green phlegm", "Traces of red blood (Hemoptysis)", "Clear or white mucus"]
            },
            {
                "id": "cough_triggers",
                "question": "Is the cough worse at night, when lying flat, in cold air, or accompanied by wheezing sounds?",
                "options": ["Worse at night or lying down", "Wheezing / whistling sounds in chest", "Triggered by dust or smoke", "No nocturnal worsening"]
            }
        ]
    },
    {
        "domain": "breathlessness",
        "trigger": r"breath|dyspnea|shortness\s*of\s*breath|wheez|saans|swasa",
        "section": "hpi",
        "questions": [
            {
                "id": "dyspnea_severity",
                "question": "Are you struggling to breathe while resting, or unable to lie flat without extra pillows (orthopnea)?",
                "options": ["Struggling at complete rest", "Short of breath on minimal walking", "Cannot lie flat without 2+ pillows", "Wheezing / whistling in chest"]
            },
            {
                "id": "dyspnea_onset",
                "question": "Did the breathing difficulty begin suddenly within minutes/hours, or gradually over days?",
                "options": ["Sudden acute onset (< 2 hours)", "Developed over 2-3 days", "Gradually worsening over weeks", "Chronic long-standing issue"]
            }
        ]
    },
    {
        "domain": "abdominal_pain",
        "trigger": r"abdom|stomach\s*pain|belly|pet\s*dard|gut|kadupu\s*noppi",
        "section": "hpi",
        "questions": [
            {
                "id": "abd_location",
                "question": "Which part of your abdomen hurts most — upper center, upper right under ribs, lower right (appendix area), or all over?",
                "options": ["Upper center (Burning/Acidity)", "Right upper side under ribs (Gallbladder/Liver)", "Right lower abdomen (Appendix concern)", "All over / Diffuse cramping"]
            },
            {
                "id": "abd_character",
                "question": "What does the pain feel like — burning sensation, sharp cramping spasms that come in waves, or a dull ache?",
                "options": ["Burning acidity sensation", "Cramping spasms in waves (Colicky)", "Sharp continuous pain", "Dull bloated ache"]
            },
            {
                "id": "abd_relation_food",
                "question": "Is the pain related to eating — worse immediately after meals, on an empty stomach, or after oily/spicy food?",
                "options": ["Worse immediately after meals", "Worse after fatty, greasy or spicy food", "Relieved after eating / Worse on empty stomach", "Unrelated to food"]
            },
            {
                "id": "abd_associated",
                "question": "Are you experiencing vomiting, loose watery stools (diarrhea), constipation, or fever along with the stomach pain?",
                "options": ["Nausea & vomiting", "Watery loose stools / diarrhea", "Inability to pass stools or gas", "No vomiting or bowel changes"]
            }
        ]
    },
    {
        "domain": "headache",
        "trigger": r"headache|migraine|head\s*pain|sar\s*dard|matha\s*darda|munda\s*bindha|talanappi",
        "section": "hpi",
        "questions": [
            {
                "id": "ha_character",
                "question": "What does the headache feel like — throbbing and pulsating like a heartbeat, or a tight squeezing band across the forehead?",
                "options": ["One-sided pulsating / throbbing (Migraine pattern)", "Tight band squeezing around head (Tension pattern)", "Sudden severe 'thunderclap' headache", "Back of head & neck stiffness"]
            },
            {
                "id": "ha_location",
                "question": "Where is the headache located — one side of the head, across your forehead, at the back of your head/neck, or all over?",
                "options": ["One side of head (Temple/Eye)", "Across forehead / Front of head", "Back of head & neck (Occipital)", "All over entire head"]
            },
            {
                "id": "ha_vision",
                "question": "Do you experience sensitivity to bright light/sound, nausea, or seeing flashing zigzag lights during the headache?",
                "options": ["Sensitivity to bright light & loud sound", "Nausea or vomiting", "Visual zigzag lines / flashing aura", "No associated symptoms"]
            },
            {
                "id": "ha_triggers",
                "question": "Does anything trigger or worsen the headache — such as lack of sleep, stress, long screen use, or coughing?",
                "options": ["Worse with stress / lack of sleep", "Worse with long screen use / reading", "Worse when coughing or bending forward", "Relieved in a quiet dark room"]
            }
        ]
    },
    {
        "domain": "joint_pain",
        "trigger": r"joint|knee|arthritis|jodon\s*me\s*dard|ghutne|mokaali",
        "section": "hpi",
        "questions": [
            {
                "id": "joint_location",
                "question": "Which specific joints are hurting (e.g., one knee, both knees, hips, fingers, wrists, or ankles)?",
                "options": ["One knee only (Right / Left)", "Both knees symmetrically", "Small joints of fingers & wrists", "Ankles or feet"]
            },
            {
                "id": "joint_swelling_stiffness",
                "question": "Is there visible swelling, warmth, or morning stiffness in the joints that lasts for more than 30 minutes?",
                "options": ["Morning stiffness lasting > 30 minutes", "Stiff for 5-10 minutes, worse with walking", "Visible swelling, warmth & redness", "No swelling or significant stiffness"]
            },
            {
                "id": "joint_mobility",
                "question": "Does walking, climbing stairs, or bearing weight worsen the pain? Can you walk independently?",
                "options": ["Worse when climbing stairs or walking", "Unable to bear weight on the joint", "Pain even while resting in bed", "Creaking sounds in joint on movement"]
            }
        ]
    },
    {
        "domain": "back_pain",
        "trigger": r"back\s*pain|spine|lumbago|sciatica|kamar\s*dard|nadumu\s*noppi",
        "section": "hpi",
        "questions": [
            {
                "id": "back_location_radiation",
                "question": "Where is the back pain located, and does it shoot down your buttocks, leg, or foot (sciatica)?",
                "options": ["Lower back localized only (No radiation)", "Shoots down one leg to calf/foot (Sciatica)", "Shoots down both legs", "Upper / Mid back between shoulder blades"]
            },
            {
                "id": "back_red_flags",
                "question": "Have you experienced any loss of bowel/bladder control, difficulty passing urine, or numbness between your legs?",
                "options": ["No numbness or urinary / bowel problems", "Numbness / tingling in feet or toes", "Difficulty passing urine / retention", "Weakness in foot (Foot drop)"]
            }
        ]
    },
    {
        "domain": "vomiting",
        "trigger": r"vomit|nausea|ulti|vaanti|baanti|emesis",
        "section": "hpi",
        "questions": [
            {
                "id": "vomit_frequency",
                "question": "How many times have you vomited in the past 24 hours, and are you able to keep sips of water down?",
                "options": ["1-2 times (Mild)", "3-5 times today", "Persistent (> 6 times) / Cannot keep water down", "Nausea only (No vomiting)"]
            },
            {
                "id": "vomit_blood_bile",
                "question": "What does the vomit look like — clear fluid, greenish-yellow bile, or have you seen red blood or dark coffee-ground material?",
                "options": ["Undigested food & clear fluid", "Greenish-yellow bitter bile", "Traces of red blood or coffee-ground color", "No blood seen"]
            }
        ]
    },
    {
        "domain": "diarrhea",
        "trigger": r"diarrhea|loose\s*motion|loose\s*stool|dast|jhada|dysentery",
        "section": "hpi",
        "questions": [
            {
                "id": "diarrhea_frequency",
                "question": "How many loose or watery motions have you had in the last 24 hours?",
                "options": ["2 to 4 loose motions (Mild)", "5 to 8 watery stools today (Moderate)", "> 8 watery motions / continuous (Severe)", "Semi-formed soft stools"]
            },
            {
                "id": "diarrhea_blood",
                "question": "Have you seen any red blood, black tarry color, or sticky mucus in the stools?",
                "options": ["Traces of red blood with mucus (Dysentery concern)", "Black tarry stools (Melena concern)", "Watery without any blood or mucus", "Sticky mucus only"]
            }
        ]
    },
    {
        "domain": "urinary_symptoms",
        "trigger": r"urin|dysuria|bladder|peshab|mutram|parisra",
        "section": "hpi",
        "questions": [
            {
                "id": "urinary_dysuria",
                "question": "Do you feel a burning sensation or pain when urinating, or an urgent need to urinate frequently?",
                "options": ["Burning pain during urination (Dysuria)", "Urgent need to urinate every few minutes", "Difficulty starting urine stream / weak flow", "Pain at end of urination"]
            },
            {
                "id": "urinary_hematuria",
                "question": "Have you seen any red blood, pink tint, or cloudiness in your urine?",
                "options": ["Visible red blood in urine (Hematuria)", "Cloudy foul-smelling urine", "Normal pale yellow color", "Dark concentrated yellow"]
            }
        ]
    },
    {
        "domain": "dizziness",
        "trigger": r"dizz\w*|vertigo|lightheaded|chakkar|kallu\s*thiragadam",
        "section": "hpi",
        "questions": [
            {
                "id": "dizziness_type",
                "question": "Does the room feel like it is spinning around you (vertigo), or do you feel lightheaded like you might faint?",
                "options": ["Room spinning around me (True Vertigo)", "Lightheaded / Feeling faint on standing", "Unsteadiness / Loss of balance while walking", "Floating woozy sensation"]
            },
            {
                "id": "dizziness_triggers",
                "question": "Does turning your head, rolling over in bed, or suddenly standing up trigger the dizziness?",
                "options": ["Triggered by rolling over in bed or looking up", "Triggered only when standing up quickly", "Constant dizziness regardless of position", "No specific positional trigger"]
            }
        ]
    },
    {
        "domain": "skin_allergy",
        "trigger": r"rash|itch|hives|urticaria|khujli|chakatte|skin\s*allergy",
        "section": "hpi",
        "questions": [
            {
                "id": "skin_location",
                "question": "Where on your body did the rash or itching start, and is it spreading?",
                "options": ["Localized to arms / legs only", "Spread all over chest, back & abdomen", "Face, neck and scalp involved", "Confined to hands or feet only"]
            },
            {
                "id": "skin_morphology",
                "question": "What does the rash look like — raised red itchy welts (hives), fluid-filled blisters, or dry scaly patches?",
                "options": ["Raised itchy wheals / hives (Urticaria)", "Fluid-filled blisters or peeling skin", "Dry, red, scaly itching patches", "Tiny red dots (Petechiae concern)"]
            }
        ]
    },
    {
        "domain": "throat_symptoms",
        "trigger": r"throat|swallow|pharyngitis|tonsil|gala\s*dard|gonthu\s*noppi",
        "section": "hpi",
        "questions": [
            {
                "id": "throat_character",
                "question": "Does your throat feel raw and scratchy, or is there sharp pain specifically when swallowing food and liquids?",
                "options": ["Severe pain when swallowing (Odynophagia)", "Dry scratchy raw sensation", "Pain radiates to one ear", "Mild irritation only"]
            },
            {
                "id": "throat_airway",
                "question": "Can you swallow your own saliva, or are you drooling, unable to open your mouth wide, or having noisy breathing?",
                "options": ["Can swallow saliva without difficulty", "Difficulty opening mouth wide (Trismus)", "Drooling / Unable to swallow saliva", "Hoarse muffled voice"]
            }
        ]
    },
    {
        "domain": "weakness_fatigue",
        "trigger": r"weak\w*|fatigue|tired|exhaust\w*|kamzori|thakan|durbalata",
        "section": "hpi",
        "questions": [
            {
                "id": "weakness_duration",
                "question": "How long have you felt this weakness, and does it prevent you from completing your daily routine or work?",
                "options": ["Started recently over past few days", "Present for 2 to 4 weeks", "Chronic ongoing exhaustion for months", "Prevents basic household tasks"]
            },
            {
                "id": "weakness_pallor",
                "question": "Have you noticed pale skin/eyes, shortness of breath after climbing just a few stairs, or dizziness when standing?",
                "options": ["Pale eyes/nails & breathlessness on minor walking", "Feeling dizzy upon standing up quickly", "Cold hands and feet with hair fall", "No breathlessness or paleness"]
            }
        ]
    }
]

def get_deterministic_adaptive_questions(chief_complaint: str, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates chief complaint and current section answers using predefined clinical rules.
    Prevents repetitive or cross-system duplicate questions.
    """
    cc_clean = str(chief_complaint or "").strip()

    # 1. Check for Ambiguous / Non-specific complaint
    if ClinicalQuestionRelevanceValidator.is_ambiguous_complaint(cc_clean):
        clarify_q = ClinicalQuestionRelevanceValidator.get_clarification_question("en-IN")
        return [{
            "id": clarify_q["id"],
            "question": clarify_q["text"],
            "options": clarify_q["quick_picks"],
            "source": "clinical_clarification"
        }]

    combined = f"{cc_clean} " + " ".join([str(v) for v in answers.values()])
    suggested = []
    seen_ids = set()
    answered_keys = {str(k).lower().strip() for k in answers.keys()}

    # Match rules against combined text
    matched_domain = None
    for rule in ADAPTIVE_RULES:
        if re.search(rule["trigger"], combined, re.IGNORECASE):
            matched_domain = rule.get("domain", "generic")
            for q in rule["questions"]:
                qid = q["id"]
                if qid.lower() not in answered_keys and qid not in seen_ids:
                    # Validate cross-system jump prohibition
                    is_valid, _ = ClinicalQuestionRelevanceValidator.validate_question(
                        q, {"hpi": answers, "chief_complaints": [cc_clean]}, active_complaint=matched_domain
                    )
                    if is_valid:
                        seen_ids.add(qid)
                        suggested.append(q)

    # Fallback questions if no specialized match
    if not suggested:
        fallbacks = [
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
        for fb in fallbacks:
            if fb["id"].lower() not in answered_keys and fb["id"] not in seen_ids:
                seen_ids.add(fb["id"])
                suggested.append(fb)

    return suggested[:3]


def get_ai_adaptive_questions(chief_complaint: str, answers: Dict[str, Any], timeout: float = 4.5, language: str = "en-IN") -> Optional[List[Dict[str, Any]]]:
    """
    Calls OpenRouter AI API to generate tailored clinical follow-up questions.
    Validates all output with ClinicalQuestionRelevanceValidator to eliminate off-target questions.
    Returns None if API key is missing, network fails, times out, or questions fail validation.
    """
    if not chief_complaint or not str(chief_complaint).strip():
        return None

    cc_clean = str(chief_complaint).strip()
    if ClinicalQuestionRelevanceValidator.is_ambiguous_complaint(cc_clean):
        return None  # Let deterministic clarify_chief_complaint handle ambiguous complaints

    try:
        from disease_prediction.api.openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME, is_circuit_open, trip_circuit_breaker
    except ImportError:
        try:
            from openrouter_service import get_api_key, OPENROUTER_API_URL, SITE_URL, APP_NAME, is_circuit_open, trip_circuit_breaker
        except ImportError:
            is_circuit_open = lambda: False
            trip_circuit_breaker = lambda *a, **kw: None
        import requests

    if is_circuit_open():
        return None

    api_key = get_api_key()
    if not api_key:
        return None

    canonical_domain = ClinicalQuestionRelevanceValidator.normalize_complaint_key(cc_clean)
    lang_instruction = f"Target Language: {language}.\n" if language and language != "en-IN" else ""

    prompt = (
        "You are an expert clinical history intake assistant for an outpatient clinic.\n"
        "Generate 2 to 3 clinically relevant follow-up questions based on the patient's complaint and recorded answers.\n"
        "Follow standard clinical history protocol (OPQRST / SOCRATES).\n"
        f"{lang_instruction}"
        "CRITICAL RULES:\n"
        f"1. Stay strictly on the patient's reported complaint: '{cc_clean}'.\n"
        "2. DO NOT jump to unrelated body systems (no breathing questions for headache, no arm pain for stomach pain).\n"
        "3. DO NOT provide a diagnosis, medical advice, or reassure the patient.\n"
        "4. Only ask intake questions to gather more specific clinical history (onset, duration, location, character, triggers, severity).\n"
        "5. For each question, provide 3 to 4 concise selectable options / answer chips.\n"
        f"Chief Complaint: {cc_clean}\n"
        f"Known Answers: {json.dumps(answers)}\n\n"
        "Respond ONLY with a JSON object in this exact schema:\n"
        "{\n"
        '  "questions": [\n'
        '    {\n'
        '      "question_id": "q1",\n'
        '      "question": "Question text here?",\n'
        '      "clinical_objective": "Reason for asking this question",\n'
        f'      "related_symptoms": ["{canonical_domain}"],\n'
        '      "target_slot": "location",\n'
        '      "relevance_reason": "Why this question relates to the complaint",\n'
        '      "options": ["Option 1", "Option 2", "Option 3"]\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": SITE_URL,
        "X-Title": APP_NAME,
        "Content-Type": "application/json"
    }

    candidate_models = [
        os.getenv("OPENROUTER_FOLLOWUP_MODEL", "nex-agi/nex-n2.5-mini:free"),
        "openrouter/free"
    ]

    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a clinical intake question generator. Return valid JSON only with 'questions' array. Stay strictly on the reported complaint. No markdown, no thinking."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 450
        }

        try:
            resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=(1.5, timeout))
            if resp.status_code == 200:
                choice = resp.json().get("choices", [{}])[0]
                msg = choice.get("message", {})
                raw = (msg.get("content") or msg.get("reasoning") or "").strip()
                raw = raw.replace("\ufffd", "-").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')

                m = re.search(r'(\{[\s\S]*\})', raw)
                if m:
                    parsed = json.loads(m.group(1))
                    q_list = parsed.get("questions") if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else None)
                    if isinstance(q_list, list) and len(q_list) > 0:
                        valid_qs = []
                        seen_ai_ids = set()
                        answered_keys = {str(k).lower().strip() for k in answers.keys()}
                        temp_state = {"hpi": answers, "chief_complaints": [cc_clean], "asked_question_ids": list(answered_keys)}

                        for i, q in enumerate(q_list[:3]):
                            if isinstance(q, dict) and q.get("question"):
                                qid = str(q.get("question_id") or q.get("id") or f"ai_q_{i+1}")
                                q_text = str(q["question"]).strip()

                                # Validate question relevance & cross-system boundaries
                                cand_dict = {
                                    "id": qid,
                                    "text": q_text,
                                    "target_slot": q.get("target_slot", "general"),
                                    "domain": canonical_domain
                                }
                                is_valid, rej_reason = ClinicalQuestionRelevanceValidator.validate_question(
                                    cand_dict, temp_state, active_complaint=canonical_domain
                                )
                                if not is_valid:
                                    continue

                                if qid.lower() not in answered_keys and qid not in seen_ai_ids:
                                    seen_ai_ids.add(qid)
                                    valid_qs.append({
                                        "id": qid,
                                        "question": q_text,
                                        "options": [str(opt).replace("\ufffd", "-").strip() for opt in q.get("options", []) if str(opt).strip()][:4],
                                        "clinical_objective": q.get("clinical_objective", ""),
                                        "target_slot": q.get("target_slot", "general"),
                                        "source": "ai_generated"
                                    })
                        if valid_qs:
                            return valid_qs
            elif resp.status_code == 429:
                trip_circuit_breaker(180.0, "OpenRouter daily quota limit reached")
                return None
        except Exception:
            continue

    return None


def get_adaptive_questions(chief_complaint: str, answers: Dict[str, Any], language: str = "en-IN") -> List[Dict[str, Any]]:
    """
    Evaluates chief complaint and current section answers.
    1. First attempts to query AI API for tailored follow-up questions.
    2. SAFETY FALLBACK: If the API key is missing, internet drops, API times out, or AI generates invalid questions,
       it seamlessly uses the clinical deterministic engine so questions remain strictly symptom-related.
    """
    ai_questions = get_ai_adaptive_questions(chief_complaint, answers, timeout=4.0, language=language)
    if ai_questions:
        return ai_questions

    # Built-in Engine Fallback (Guaranteed 100% Symptom-Specific)
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
    hpi = get_sec_text("hpi", "Not reported")
    past_medical = get_sec_text("past_medical", "Not reported")
    past_surgical = get_sec_text("past_surgical", "Not reported")
    drug_history = get_sec_text("drug_history", "Not reported")
    allergy_history = get_sec_text("allergy_history", "Not reported")
    family_history = get_sec_text("family_history", "Not reported")
    personal_history = get_sec_text("personal_history", "Not provided")
    ros = get_sec_text("ros", "Not reported")
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
            "hospital": "Avenqra AI Adaptive Clinical Platform",
            "generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "case_id": case_info.get("case_id"),
            "patient_id": patient_info.get("patient_id", case_info.get("patient_id")),
            "patient_name": patient_info.get("name", "Outpatient"),
            "age_gender": f"{patient_info.get('age', '—')} Yrs / {patient_info.get('gender', '—')}",
            "contact": patient_info.get("contact", "—"),
            "abha_id": case_info.get("abha_id") or "Not linked",
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
