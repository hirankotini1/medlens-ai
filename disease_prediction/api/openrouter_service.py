"""
MEDLENS — OpenRouter AI Service & Rare Disease Pattern Screening Engine
Handles communication with OpenRouter API models, PII de-identification,
JSON sanitization, multi-biomarker concordance detection, and evidence-based clinical decision support.
"""

import os 
import json 
import re 
import requests 
from typing import Dict ,Any ,List ,Optional 
from pathlib import Path 
from dotenv import load_dotenv 
from disease_prediction .api import rare_disease_engine 


env_path =Path (__file__ ).resolve ().parent .parent /".env"
if env_path .exists ():
    load_dotenv (dotenv_path =env_path )
else :
    load_dotenv ()

OPENROUTER_API_URL ="https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL =os .getenv ("OPENROUTER_MODEL","openrouter/auto")
SITE_URL =os .getenv ("OPENROUTER_SITE_URL","http://localhost:8000")
APP_NAME =os .getenv ("OPENROUTER_APP_NAME","MEDLENS AI Health Report Analyzer")


def get_api_key ()->str :
    """Retrieve OpenRouter API key from environment."""
    key =os .getenv ("OPENROUTER_API_KEY","")
    if not key or key .strip ()==""or "your_openrouter_api_key_here"in key :
        return ""
    return key .strip ()


def strip_pii_from_payload (parameters :List [Dict [str ,Any ]],patient_meta :Optional [Dict [str ,Any ]]=None )->Dict [str ,Any ]:
    """
    Strictly removes Personally Identifiable Information (PII) before sending data to external AI.
    Never sends full names, patient IDs, report IDs, phone numbers, emails, or addresses.
    Preserves only clinical age and biological sex for demographic context.
    """
    clean_meta ={}
    if patient_meta :
        if "age"in patient_meta and patient_meta ["age"]is not None :
            clean_meta ["age"]=patient_meta ["age"]
        if "gender"in patient_meta and patient_meta ["gender"]:
            clean_meta ["biological_sex"]=patient_meta ["gender"]

    clean_params =[]
    for p in parameters :
        clean_params .append ({
        "parameter":str (p .get ("parameter","")),
        "canonical_key":str (p .get ("canonical_key","")),
        "value":p .get ("value"),
        "unit":str (p .get ("unit","")),
        "reference_range":str (p .get ("reference_range","")),
        "status":str (p .get ("status","NORMAL")).upper ()
        })

    return {
    "demographics":clean_meta ,
    "laboratory_findings":clean_params 
    }


def clean_json_response (raw_text :str )->Dict [str ,Any ]:
    """Clean markdown code fences and extract valid JSON dictionary."""
    text =raw_text .strip ()

    if text .startswith ("```json"):
        text =text [7 :]
    elif text .startswith ("```"):
        text =text [3 :]
    if text .endswith ("```"):
        text =text [:-3 ]
    text =text .strip ()

    try :
        return json .loads (text )
    except json .JSONDecodeError :
        match =re .search (r'(\{[\s\S]*\})',text )
        if match :
            try :
                return json .loads (match .group (1 ))
            except json .JSONDecodeError :
                pass 

    raise ValueError ("AI response did not contain valid JSON.")


def enforce_clinical_guardrails (
analysis :Dict [str ,Any ],
parameters :Optional [List [Dict [str ,Any ]]]=None ,
patient_meta :Optional [Dict [str ,Any ]]=None 
)->Dict [str ,Any ]:
    """
    Enforce clinical non-autonomous guardrails:
    1. Ensure cautious screening wording (no 'confirmed diagnosis', no prescribing medications or treatments).
    2. Ensure rare-disease screening evidence structure and candidate conditions list are present.
    3. Ensure limitations and disclaimers are present.
    """
    summary =analysis .get ("summary","")
    summary =re .sub (r"\b(you have|patient has|patient is suffering from|diagnosed with|confirmed diagnosis of|guaranteed to be|definitive diagnosis)\b","findings suggest a possible pattern of",summary ,flags =re .IGNORECASE )
    analysis ["summary"]=summary 


    conditions =analysis .get ("possible_conditions",[])
    safe_conditions =[]
    for c in conditions :
        if isinstance (c ,dict ):
            name =c .get ("name","Unspecified Observation")
            name =re .sub (r"\b(Definitive|Confirmed|Diagnosed)\b","Possible",name ,flags =re .IGNORECASE )
            strength =str (c .get ("strength")or c .get ("likelihood_category")or "MODERATE").upper ()
            if strength not in ["HIGH","MODERATE","LOW"]:
                strength ="MODERATE"


            follow_ups =c .get ("suggested_follow_up",[])
            safe_follow_ups =[]
            for f in follow_ups :
                f_str =str (f )
                if not any (w in f_str .lower ()for w in ["mg","dose","tablet","capsule","prescribe","inject","take "]):
                    safe_follow_ups .append (f_str )
            if not safe_follow_ups :
                safe_follow_ups =["Clinical correlation and diagnostic review with an attending physician."]

            safe_conditions .append ({
            "name":name ,
            "strength":strength ,
            "likelihood_category":strength .lower (),
            "reason":c .get ("reason","Correlated with abnormal laboratory biomarkers."),
            "supporting_findings":c .get ("supporting_findings",[]),
            "suggested_follow_up":safe_follow_ups 
            })
    analysis ["possible_conditions"]=safe_conditions 


    diff_diag =analysis .get ("differential_diagnosis",[])
    safe_diff =[]
    if isinstance (diff_diag ,list ):
        for item in diff_diag [:2 ]:
            if isinstance (item ,dict ):
                cond =item .get ("condition")or "Diagnostic Consideration"
                sup =item .get ("supporting_evidence")or ["Elevated or depressed biomarker pattern observed in report."]
                con =item .get ("contradicting_evidence")or ["Normal parameters outside primary panel findings."]
                safe_diff .append ({
                "condition":cond ,
                "supporting_evidence":[str (s )for s in sup ]if isinstance (sup ,list )else [str (sup )],
                "contradicting_evidence":[str (c )for c in con ]if isinstance (con ,list )else [str (con )]
                })
    if not safe_diff :
        first_cond =safe_conditions [0 ]["name"]if safe_conditions else "Primary Clinical Presentation"
        second_cond =safe_conditions [1 ]["name"]if len (safe_conditions )>1 else "Alternative Metabolic / Reactive Etiology"
        safe_diff =[
        {
        "condition":first_cond ,
        "supporting_evidence":["Correlated abnormal biomarker values detected during screening."],
        "contradicting_evidence":["Absence of acute multi-organ decompensation flags in baseline parameters."]
        },
        {
        "condition":second_cond ,
        "supporting_evidence":["Overlapping biochemical reference range deviations across secondary markers."],
        "contradicting_evidence":["Primary differential candidate exhibits stronger biomarker concordance."]
        }
        ]
    analysis ["differential_diagnosis"]=safe_diff [:2 ]


    missing =analysis .get ("missing_tests",[])
    if not isinstance (missing ,list )or len (missing )==0 :
        missing =[
        "Complete Blood Count (CBC) with Peripheral Smear",
        "Comprehensive Metabolic / Liver Panel (LFT)",
        "Serum Ferritin & Iron Studies",
        "Urinary Protein-to-Creatinine Ratio"
        ]
    analysis ["missing_tests"]=[str (m )for m in missing ]


    hidden =analysis .get ("hidden_abnormalities",[])
    safe_hidden =[]
    if isinstance (hidden ,list ):
        for h in hidden :
            if isinstance (h ,dict )and "biomarkers"in h and "implication"in h :
                safe_hidden .append ({
                "biomarkers":[str (b )for b in h ["biomarkers"]]if isinstance (h ["biomarkers"],list )else [str (h ["biomarkers"])],
                "implication":str (h ["implication"])
                })
    if not safe_hidden and parameters :
        borderline_found =[]
        for p in parameters :
            val =p .get ("value")
            try :
                val_f =float (val )
                ck =str (p .get ("canonical_key","")).upper ()
                if ck =="HGB"and 11.5 <=val_f <=12.5 :
                    borderline_found .append (f"Hemoglobin ({val_f } g/dL, Lower-Normal)")
                elif ck =="MCV"and 80.0 <=val_f <=83.0 :
                    borderline_found .append (f"MCV ({val_f } fL, Lower-Normal)")
                elif ck in ["PLT","PLATELET_COUNT"]and 150000 <=val_f <=180000 :
                    borderline_found .append (f"Platelet Count ({int (val_f ):,} /µL, Lower-Normal)")
                elif ck =="TOTAL_BILIRUBIN"and 1.0 <=val_f <=1.2 :
                    borderline_found .append (f"Total Bilirubin ({val_f } mg/dL, Upper-Normal)")
                elif ck =="TSH"and 3.5 <=val_f <=4.2 :
                    borderline_found .append (f"TSH ({val_f } µIU/mL, Upper-Normal)")
            except (ValueError ,TypeError ):
                pass 
        if len (borderline_found )>=2 :
            safe_hidden .append ({
            "biomarkers":borderline_found [:2 ],
            "implication":"Concurrently clustered lower/upper limits within reference range indicate early latent subclinical strain before overt flag triggers."
            })
    analysis ["hidden_abnormalities"]=safe_hidden 


    rare_screening =analysis .get ("rare_unusual_screening")
    if not isinstance (rare_screening ,dict ):
        rare_screening ={}


    if parameters is not None :
        engine_eval =rare_disease_engine .evaluate_rare_disease_patterns (parameters ,patient_meta )
        rare_screening ["flagged"]=engine_eval ["flagged"]
        rare_screening ["conditions"]=engine_eval ["conditions"]
        rare_screening ["conditions_count"]=engine_eval ["conditions_count"]
        rare_screening ["top_screening_patterns"]=engine_eval .get ("top_screening_patterns",[])
        rare_screening ["unsupported_conditions"]=engine_eval .get ("unsupported_conditions",[])
        rare_screening ["condition_name"]=engine_eval ["condition_name"]
        rare_screening ["screening_strength"]=engine_eval ["screening_strength"]
        rare_screening ["why_flagged"]=engine_eval ["why_flagged"]
        rare_screening ["supporting_findings"]=engine_eval ["supporting_findings"]
        rare_screening ["confirmatory_evaluation"]=engine_eval ["confirmatory_evaluation"]
        rare_screening ["disclaimer"]=engine_eval ["disclaimer"]

    if "conditions"not in rare_screening :
        rare_screening ["conditions"]=[]
        rare_screening ["conditions_count"]=0 
    if "top_screening_patterns"not in rare_screening :
        rare_screening ["top_screening_patterns"]=[]
    if "unsupported_conditions"not in rare_screening :
        rare_screening ["unsupported_conditions"]=[]
    if "condition_name"not in rare_screening or not rare_screening ["condition_name"]:
        rare_screening ["condition_name"]="No specific rare condition identified"
    if "screening_strength"not in rare_screening or not rare_screening ["screening_strength"]:
        rare_screening ["screening_strength"]="NONE"

    analysis ["rare_unusual_screening"]=rare_screening 
    analysis ["possible_rare_unusual_screening"]=rare_screening .get ("why_flagged","")


    precautions =analysis .get ("general_precautions",[])
    safe_precautions =[]
    forbidden_terms =["mg","dose","tablet","capsule","antibiotic","prescription","take 500","supplementation of","inject","treat with"]
    for p in precautions :
        if not any (t in str (p ).lower ()for t in forbidden_terms ):
            safe_precautions .append (str (p ))

    if not safe_precautions :
        safe_precautions =[
        "Discuss these findings with a qualified healthcare professional, who can determine appropriate follow-up.",
        "Avoid self-medicating or adjusting existing therapies without medical supervision.",
        "Maintain adequate hydration and balanced nutrition under clinical guidance.",
        "Complete recommended confirmatory diagnostic testing as guided by your physician."
        ]
    analysis ["general_precautions"]=safe_precautions 

    analysis ["limitations"]=[
    "This is an experimental AI-assisted decision-support analysis for educational and research review.",
    "It does not constitute a clinical medical diagnosis, prescription, or therapeutic directive."
    ]

    return analysis 


def analyze_report_with_ai (
parameters :List [Dict [str ,Any ]],
patient_meta :Optional [Dict [str ,Any ]]=None ,
image_b64 :Optional [str ]=None ,
model_override :Optional [str ]=None 
)->Dict [str ,Any ]:
    """
    Analyzes structured laboratory parameters using OpenRouter AI.
    Falls back gracefully to deterministic rule-based clinical heuristics if offline.
    """
    api_key =get_api_key ()
    if not api_key :
        return get_fallback_analysis (parameters ,patient_meta ,reason ="OpenRouter API Key not configured. Using verified clinical heuristic engine.")

    model =model_override or os .getenv ("OPENROUTER_MODEL",DEFAULT_MODEL )
    clean_payload =strip_pii_from_payload (parameters ,patient_meta )

    system_prompt ="""You are a clinical pathology decision-support AI in MEDLENS. Analyze lab findings and return ONLY valid JSON — no markdown.

RULES:
- Never make autonomous diagnoses. Use: "Possible pattern", "Findings consistent with...", "Screening signal only".
- Never prescribe medications or doses.
- For rare disease screening, use multi-marker combinations, not single tests.
- Use screening strengths: HIGH / MODERATE / LOW. No invented probabilities.
- Provide top 2 Differential Diagnosis candidates with explicit supporting and contradicting laboratory evidence.
- Identify Missing Tests required to confirm the differential diagnosis.
- Detect Hidden Abnormalities (borderline values within normal intervals that synergistically suggest subclinical or early-stage pathology).

Return exactly this JSON schema:
{
  "summary": "2-3 sentence clinical overview.",
  "overall_attention": "NORMAL|MODERATE ATTENTION|HIGH ATTENTION / ELEVATED RISK",
  "abnormal_findings": [
    {"parameter": "Name", "value": "Value+Unit", "status": "LOW|HIGH|CRITICAL", "significance": "Brief pathophysiological note"}
  ],
  "differential_diagnosis": [
    {
      "condition": "Condition Name",
      "supporting_evidence": ["Evidence pointing towards this diagnosis"],
      "contradicting_evidence": ["Evidence or normal findings pointing away from this diagnosis"]
    }
  ],
  "missing_tests": ["Confirmatory Test 1", "Confirmatory Test 2"],
  "hidden_abnormalities": [
    {
      "biomarkers": ["Biomarker A", "Biomarker B"],
      "implication": "Clinical implication of synergistic borderline values"
    }
  ],
  "patterns": [
    {"name": "Pattern Name", "strength": "HIGH|MODERATE|LOW", "why_flagged": "Rationale", "supporting_findings": ["Finding"], "suggested_follow_up": ["Step"]}
  ],
  "rare_unusual_screening": {
    "flagged": true,
    "condition_name": "Name",
    "screening_strength": "HIGH|MODERATE|LOW|NONE",
    "why_flagged": "Multi-marker rationale",
    "supporting_findings": ["Biomarker"],
    "confirmatory_evaluation": "Tests needed",
    "disclaimer": "Screening signal only."
  },
  "general_precautions": ["Recommendation"]
}"""

    user_content =f"""Please analyze the following de-identified laboratory test findings:
Demographic Context: {json .dumps (clean_payload ['demographics'])}
Laboratory Findings:
{json .dumps (clean_payload ['laboratory_findings'],indent =2 )}

Generate a structured clinical decision-support analysis adhering strictly to the JSON schema."""

    lang =(patient_meta or {}).get ("language")or "English"
    if str (lang ).lower ()!="english":
        system_prompt +=f"\n\nLANGUAGE INSTRUCTION: Provide all explanatory values, summaries, pathophysiological notes, and recommendations strictly in {lang }. Keep parameter names in standard clinical format."

    messages =[
    {"role":"system","content":system_prompt },
    {"role":"user","content":user_content }
    ]

    headers ={
    "Authorization":f"Bearer {api_key }",
    "HTTP-Referer":SITE_URL ,
    "X-Title":APP_NAME ,
    "Content-Type":"application/json"
    }


    preferred_model =os .getenv ("OPENROUTER_MODEL","google/gemma-4-31b-it:free")
    candidate_models =[
    preferred_model ,
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m3:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-26b-a4b-it:free",
    "openrouter/free",
    "openrouter/auto"
    ]

    seen =set ()
    candidate_models =[m for m in candidate_models if m and not (m in seen or seen .add (m ))]

    last_error =None 
    for cand_model in candidate_models :
        payload ={
        "model":cand_model ,
        "messages":messages ,
        "temperature":0.1 ,
        "max_tokens":1400 
        }
        try :

            resp =requests .post (OPENROUTER_API_URL ,headers =headers ,json =payload ,timeout =(3.0 ,8.0 ))
            if resp .status_code ==200 :
                resp_json =resp .json ()
                content =resp_json ["choices"][0 ]["message"]["content"]
                parsed =clean_json_response (content )
                parsed ["ai_model_used"]=cand_model 
                if "patterns"in parsed and "possible_conditions"not in parsed :
                    parsed ["possible_conditions"]=parsed ["patterns"]
                return enforce_clinical_guardrails (parsed ,parameters ,patient_meta )
            else :
                last_error =f"HTTP {resp .status_code }: {resp .text [:200 ]}"
        except Exception as e :
            last_error =str (e )
            continue 

    return get_fallback_analysis (parameters ,patient_meta ,reason =f"AI service temporarily unavailable ({last_error }). Evaluated with rule-based heuristics.")


def get_fallback_analysis (
parameters :List [Dict [str ,Any ]],
patient_meta :Optional [Dict [str ,Any ]]=None ,
reason :str =""
)->Dict [str ,Any ]:
    """
    High-reliability deterministic fallback clinical pattern engine.
    Evaluates multi-marker concordance for common and rare disease patterns.
    """
    patient_meta =patient_meta or {}
    age =patient_meta .get ("age",30 )
    try :
        age_val =float (age )if age is not None else 30.0 
    except (ValueError ,TypeError ):
        age_val =30.0 

    abnormal =[]
    param_map :Dict [str ,Dict [str ,Any ]]={}

    for p in parameters :
        status =str (p .get ("status","NORMAL")).upper ()
        c_key =str (p .get ("canonical_key","")).upper ()
        p_name =str (p .get ("parameter","")).lower ()

        if c_key :param_map [c_key ]=p 
        if p_name :param_map [p_name ]=p 

        if status in ["LOW","HIGH","CRITICAL","CRITICAL LOW","CRITICAL HIGH","ABNORMAL"]:
            abnormal .append ({
            "parameter":str (p .get ("parameter","")),
            "value":f"{p .get ('value')} {p .get ('unit','')}".strip (),
            "status":status ,
            "significance":f"Parameter outside reference interval ({p .get ('reference_range','N/A')})."
            })

    is_high_risk =any ("CRITICAL"in a ["status"]for a in abnormal )or len (abnormal )>=4 
    overall_attention ="HIGH ATTENTION / ELEVATED RISK"if is_high_risk else ("MODERATE ATTENTION"if abnormal else "NORMAL")

    conditions =[]





    rare_screening =rare_disease_engine .evaluate_rare_disease_patterns (parameters ,patient_meta )


    if rare_screening .get ("flagged")and rare_screening .get ("conditions"):
        for rc in rare_screening ["conditions"]:
            conditions .append ({
            "name":rc ["name"],
            "strength":rc ["screening_strength"],
            "likelihood_category":rc ["screening_strength"].lower (),
            "reason":rc ["why_flagged"],
            "supporting_findings":rc ["supporting_findings"],
            "suggested_follow_up":rc ["confirmatory_evaluation"][:3 ]
            })





    hgb =param_map .get ("HGB")or param_map .get ("hemoglobin")
    mcv =param_map .get ("MCV")or param_map .get ("mcv")
    rdw =param_map .get ("RDW")or param_map .get ("rdw")
    ferritin =param_map .get ("FERRITIN")or param_map .get ("ferritin")

    if hgb and str (hgb .get ("status","")).upper ()in ["LOW","CRITICAL LOW"]:
        supp_anemia =[f"Hemoglobin: {hgb .get ('value')} {hgb .get ('unit','g/dL')} (LOW)"]
        is_microcytic =(mcv and str (mcv .get ("status","")).upper ()=="LOW")or (ferritin and str (ferritin .get ("status","")).upper ()=="LOW")
        if is_microcytic :
            if mcv and str (mcv .get ("status","")).upper ()=="LOW":
                supp_anemia .append (f"MCV: {mcv .get ('value')} {mcv .get ('unit','fL')} (LOW - Microcytosis)")
            if rdw and str (rdw .get ("status","")).upper ()=="HIGH":
                supp_anemia .append (f"RDW: {rdw .get ('value')} {rdw .get ('unit','%')} (HIGH - Anisocytosis)")
            if ferritin and str (ferritin .get ("status","")).upper ()=="LOW":
                supp_anemia .append (f"Ferritin: {ferritin .get ('value')} {ferritin .get ('unit','ng/mL')} (LOW - Iron Depletion)")

            conditions .append ({
            "name":"Possible Microcytic / Iron-Deficiency-Type Anemia Pattern",
            "strength":"HIGH",
            "likelihood_category":"high",
            "reason":"Depressed Hemoglobin with microcytic indices (low MCV, high RDW) and/or low Ferritin.",
            "supporting_findings":supp_anemia ,
            "suggested_follow_up":["Serum Ferritin & Iron studies confirmation","Physician hematology review","Dietary assessment"]
            })
        else :
            conditions .append ({
            "name":"Possible Anemic Hematological Pattern",
            "strength":"MODERATE",
            "likelihood_category":"moderate",
            "reason":"Observed Hemoglobin is below normal biological reference range.",
            "supporting_findings":supp_anemia ,
            "suggested_follow_up":["Complete Blood Count (CBC) review","Serum Iron / Ferritin panel","Physician consultation"]
            })


    plt =param_map .get ("PLT")or param_map .get ("platelet_count")or param_map .get ("platelets")
    if plt and str (plt .get ("status","")).upper ()in ["LOW","CRITICAL LOW"]:
        conditions .append ({
        "name":"Possible Thrombocytopenic / Viral Infection Pattern",
        "strength":"MODERATE",
        "likelihood_category":"moderate",
        "reason":"Platelet count is depressed below normal biological baseline.",
        "supporting_findings":[f"Platelets: {plt .get ('value')} {plt .get ('unit','/µL')} (LOW)"],
        "suggested_follow_up":["Repeat Platelet Count in 24-48h","Dengue NS1 / IgM serology if febrile","Clinical monitoring"]
        })


    alt =param_map .get ("ALT")or param_map .get ("alanine aminotransferase")
    ast =param_map .get ("AST")or param_map .get ("aspartate aminotransferase")
    tbili =param_map .get ("TOTAL_BILIRUBIN")or param_map .get ("total bilirubin")
    has_liver_injury =(
    (alt and str (alt .get ("status","")).upper ()=="HIGH")or 
    (ast and str (ast .get ("status","")).upper ()=="HIGH")or 
    (tbili and str (tbili .get ("status","")).upper ()=="HIGH")
    )
    if has_liver_injury and not any ("Wilson"in c ["name"]or "Hemochromatosis"in c ["name"]or "Autoimmune Hepatitis"in c ["name"]for c in conditions ):
        supp_lft =[]
        if tbili and str (tbili .get ("status","")).upper ()=="HIGH":supp_lft .append (f"Total Bilirubin: {tbili .get ('value')} {tbili .get ('unit','mg/dL')} (HIGH)")
        if alt and str (alt .get ("status","")).upper ()=="HIGH":supp_lft .append (f"ALT: {alt .get ('value')} {alt .get ('unit','U/L')} (HIGH)")
        if ast and str (ast .get ("status","")).upper ()=="HIGH":supp_lft .append (f"AST: {ast .get ('value')} {ast .get ('unit','U/L')} (HIGH)")
        conditions .append ({
        "name":"Possible Hepatobiliary Biomarker Elevation",
        "strength":"MODERATE",
        "likelihood_category":"moderate",
        "reason":"Liver enzymes or bilirubin elevated above standard reference intervals.",
        "supporting_findings":supp_lft ,
        "suggested_follow_up":["Comprehensive Liver Function Test (LFT)","Abdominal Ultrasound","Gastroenterologist consultation"]
        })


    tsh =param_map .get ("TSH")or param_map .get ("tsh")
    if tsh and str (tsh .get ("status","")).upper ()in ["HIGH","CRITICAL HIGH"]:
        conditions .append ({
        "name":"Possible Hypothyroidism Pattern",
        "strength":"MODERATE",
        "likelihood_category":"moderate",
        "reason":"Elevated TSH suggests compensatory pituitary stimulation.",
        "supporting_findings":[f"TSH: {tsh .get ('value')} {tsh .get ('unit','µIU/mL')} (HIGH)"],
        "suggested_follow_up":["Free T3 and Free T4 confirmation","Anti-TPO Antibody evaluation","Endocrinologist consultation"]
        })
    elif tsh and str (tsh .get ("status","")).upper ()in ["LOW","CRITICAL LOW"]:
        conditions .append ({
        "name":"Possible Hyperthyroidism Pattern",
        "strength":"MODERATE",
        "likelihood_category":"moderate",
        "reason":"Suppressed TSH concentration below physiological reference limits.",
        "supporting_findings":[f"TSH: {tsh .get ('value')} {tsh .get ('unit','µIU/mL')} (LOW)"],
        "suggested_follow_up":["Free T3 and Free T4 confirmation","Thyroid Ultrasound / Scan","Endocrinologist consultation"]
        })

    if not conditions :
        if abnormal :
            conditions .append ({
            "name":"Atypical Laboratory Biomarker Deviation",
            "strength":"MODERATE",
            "likelihood_category":"moderate",
            "reason":"One or more clinical parameters deviated from standard biological reference intervals.",
            "supporting_findings":[f"{a ['parameter']}: {a ['value']} ({a ['status']})"for a in abnormal [:3 ]],
            "suggested_follow_up":["Clinical correlation with attending physician"]
            })
        else :
            conditions .append ({
            "name":"Standard Physiological Profile",
            "strength":"LOW",
            "likelihood_category":"low",
            "reason":"All extracted laboratory parameters are within normal biological reference intervals.",
            "supporting_findings":["All tested biomarkers within reference limits"],
            "suggested_follow_up":["Periodic routine wellness checkup"]
            })

    summary =f"Evaluation completed across {len (parameters )} laboratory parameters. Identified {len (abnormal )} parameter(s) outside standard reference intervals."
    if reason :
        summary +=f" ({reason })"

    return enforce_clinical_guardrails ({
    "summary":summary ,
    "overall_attention":overall_attention ,
    "abnormal_findings":abnormal ,
    "possible_conditions":conditions ,
    "patterns":conditions ,
    "rare_unusual_screening":rare_screening ,
    "possible_rare_unusual_screening":rare_screening ["why_flagged"],
    "general_precautions":[
    "Discuss abnormal findings with a qualified healthcare professional.",
    "Avoid self-medicating or modifying existing therapies without medical supervision.",
    "Maintain balanced nutrition and adequate hydration under clinical guidance.",
    "Complete recommended confirmatory diagnostic testing as guided by your physician."
    ],
    "ai_model_used":"Nexus Clinical Decision Heuristic (Multi-Disease Engine)"
    },parameters =parameters ,patient_meta =patient_meta )

