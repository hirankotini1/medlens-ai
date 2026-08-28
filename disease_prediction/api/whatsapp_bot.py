"""
MEDLENS AI - Twilio WhatsApp Chatbot Engine
============================================
Full multi-turn conversational chatbot with persistent SQLite session state.
Handles: symptom triage, patient report lookup, ML predictions, emergency guidance, doctor finder.

Twilio WhatsApp Sandbox: whatsapp:+14155238886
Webhook: POST /api/whatsapp/webhook
"""

import os
import json
import sqlite3
import re
import requests as _requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# ─── Environment ────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path if _env_path.exists() else None)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM        = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
BASE_URL           = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000")

# ─── Conversation State Constants ────────────────────────────────────────────
STATE_MENU         = "MENU"
STATE_SYMPTOM      = "SYMPTOM_INPUT"
STATE_PATIENT_ID   = "PATIENT_ID_INPUT"
STATE_PIN          = "PIN_INPUT"
STATE_PATIENT_DASH = "PATIENT_DASHBOARD"
STATE_EMERGENCY    = "EMERGENCY_INPUT"
SESSION_TTL_HOURS  = 4

# ─── Session Store (SQLite) ──────────────────────────────────────────────────
_DB_PATH = Path(__file__).resolve().parent.parent / "pathology.db"


def _get_conn():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_session_table():
    """Create whatsapp_sessions table if it does not exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_sessions (
            phone        TEXT PRIMARY KEY,
            state        TEXT NOT NULL DEFAULT 'MENU',
            patient_id   TEXT,
            patient_name TEXT,
            data         TEXT,
            updated_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_session(phone: str) -> Dict[str, Any]:
    """Retrieve or initialise a session for a given phone number."""
    _ensure_session_table()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM whatsapp_sessions WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    if not row:
        return {"phone": phone, "state": STATE_MENU, "patient_id": None,
                "patient_name": None, "data": {}}
    updated = datetime.fromisoformat(row["updated_at"])
    if datetime.now() - updated > timedelta(hours=SESSION_TTL_HOURS):
        clear_session(phone)
        return {"phone": phone, "state": STATE_MENU, "patient_id": None,
                "patient_name": None, "data": {}}
    return {"phone": row["phone"], "state": row["state"], "patient_id": row["patient_id"],
            "patient_name": row["patient_name"], "data": json.loads(row["data"] or "{}")}


def save_session(phone: str, state: str, patient_id: Optional[str] = None,
                 patient_name: Optional[str] = None, data: Optional[Dict] = None):
    """Upsert a session record."""
    _ensure_session_table()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO whatsapp_sessions (phone, state, patient_id, patient_name, data, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(phone) DO UPDATE SET
            state        = excluded.state,
            patient_id   = excluded.patient_id,
            patient_name = excluded.patient_name,
            data         = excluded.data,
            updated_at   = excluded.updated_at
    """, (phone, state, patient_id, patient_name,
          json.dumps(data or {}), datetime.now().isoformat()))
    conn.commit()
    conn.close()


def clear_session(phone: str):
    """Delete a session (reset conversation)."""
    _ensure_session_table()
    conn = _get_conn()
    conn.execute("DELETE FROM whatsapp_sessions WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


# ─── Twilio Signature Validation ─────────────────────────────────────────────
def validate_twilio_signature(auth_token: str, signature: str,
                               url: str, params: Dict[str, str]) -> bool:
    """Validate that a webhook POST genuinely came from Twilio."""
    if not auth_token or not signature:
        return False
    try:
        from twilio.request_validator import RequestValidator
        return RequestValidator(auth_token).validate(url, params, signature)
    except ImportError:
        import hmac, hashlib, base64
        s = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
        mac = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1)
        return hmac.compare_digest(base64.b64encode(mac.digest()).decode(), signature)


def send_whatsapp_message_direct(to_number: str, message_text: str) -> bool:
    """Directly dispatches an outbound WhatsApp message via Twilio REST API."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        from_wa = TWILIO_FROM if TWILIO_FROM.startswith("whatsapp:") else f"whatsapp:{TWILIO_FROM}"
        to_wa = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        msg = client.messages.create(
            from_=from_wa,
            to=to_wa,
            body=message_text
        )
        print(f"[TWILIO-DIRECT-SENT] SID: {msg.sid} | To: {to_wa}")
        return True
    except Exception as e:
        print(f"[TWILIO-DIRECT-ERROR] {e}")
        return False


# ─── TwiML Builder ───────────────────────────────────────────────────────────
def twiml_response(message: str) -> str:
    """Wrap a reply in compliant TwiML XML using Twilio library."""
    try:
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(message)
        return str(resp)
    except Exception:
        safe = (message
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
        return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message><Body>{safe}</Body></Message></Response>'


# ─── Message Templates ───────────────────────────────────────────────────────
WELCOME_MSG = (
    "Welcome to MEDLENS AI Health Assistant!\n"
    "Powered by Medicover Clinical Platform\n\n"
    "MAIN MENU - Type a number:\n"
    "1 - Check My Symptoms (AI-powered)\n"
    "2 - View My Lab Reports and Results\n"
    "3 - EMERGENCY Guidance\n"
    "4 - Find a Medicover Doctor\n"
    "5 - My Latest ML Health Prediction\n\n"
    "Type 'reset' anytime to restart."
)

MENU_MSG = (
    "MEDLENS Main Menu - Type a number:\n"
    "1 - Check My Symptoms\n"
    "2 - View My Lab Reports\n"
    "3 - EMERGENCY Guidance\n"
    "4 - Find a Medicover Doctor\n"
    "5 - My Latest ML Prediction\n\n"
    "Type 'reset' to restart."
)

SYMPTOM_PROMPT = (
    "AI Symptom Checker\n"
    "Please describe your symptoms in detail.\n"
    "Include: what you feel, how long, and severity.\n\n"
    "Example: 'Fever since 3 days, severe headache, body ache and chills'\n\n"
    "Type 'back' to return to the menu."
)

PATIENT_ID_PROMPT = (
    "Patient Portal Login\n"
    "Please enter your Patient ID (Example: PAT-1001)\n\n"
    "Type 'back' to return to menu."
)

PIN_PROMPT = (
    "Please enter your Access PIN (Example: PIN-1001)\n\n"
    "Type 'back' to return to menu."
)

EMERGENCY_PROMPT = (
    "EMERGENCY Symptom Triage\n"
    "Describe your emergency symptoms and I will assess urgency immediately.\n\n"
    "WARNING: If experiencing chest pain, difficulty breathing,\n"
    "or loss of consciousness - CALL 112 NOW!\n\n"
    "Type your symptoms or 'back' to return."
)


# ─── Triage Engine ───────────────────────────────────────────────────────────
def compute_triage_level(symptoms: str) -> str:
    """Returns 'red', 'amber', or 'green' based on symptom keyword analysis."""
    lower = symptoms.lower()
    red_terms = [
        "chest pain", "heart attack", "cardiac arrest", "cannot breathe",
        "stopped breathing", "unconscious", "unresponsive", "collapse",
        "fainting", "syncope", "stroke", "slurred speech", "facial droop",
        "sudden weakness", "paralysis", "seizure", "convulsion",
        "severe bleeding", "coughing blood", "vomiting blood", "hemorrhage",
        "haemorrhage", "sepsis", "anaphylaxis", "swollen tongue",
        "overdose", "poisoning", "kidney failure", "liver failure",
        "critical", "emergency", "icu", "sos"
    ]
    amber_terms = [
        "high fever", "persistent vomiting", "severe headache", "severe pain",
        "extreme fatigue", "jaundice", "difficulty breathing",
        "shortness of breath", "petechiae", "dengue", "malaria",
        "bleeding gums", "nose bleed", "confusion", "dizziness",
        "palpitations", "severe diarrhea"
    ]
    for t in red_terms:
        if t in lower:
            return "red"
    for t in amber_terms:
        if t in lower:
            return "amber"
    return "green"


# ─── AI Symptom Guidance ─────────────────────────────────────────────────────
def get_ai_symptom_guidance(symptoms: str) -> str:
    """Calls OpenRouter AI for symptom guidance; falls back to heuristics."""
    api_key = OPENROUTER_API_KEY.strip()
    if not api_key or "your_openrouter" in api_key:
        return _heuristic_symptom_guidance(symptoms)

    system_msg = (
        "You are MEDLENS HealthGuide, a compassionate clinical AI. "
        "Analyze patient symptoms and respond in this WhatsApp-friendly format (max 1400 chars):\n\n"
        "Possible Conditions:\n- [2-3 possible conditions, framed as possibilities]\n\n"
        "Immediate Care Steps:\n- [3 specific safety steps]\n\n"
        "Home Care Tips:\n- [3 supportive suggestions]\n\n"
        "Suggested Tests to Discuss with Doctor:\n- [2-3 tests]\n\n"
        "When to Seek Emergency Care:\n- [2 critical red flags]\n\n"
        "RULES: Never prescribe drugs or dosages. "
        "Never give definitive diagnoses. Frame as possible/may suggest/consistent with."
    )
    user_msg = f'Patient symptoms: "{symptoms.strip()}"'
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": BASE_URL,
        "X-Title": "MEDLENS WhatsApp Bot"
    }
    models_to_try = [
        OPENROUTER_MODEL,
        "google/gemma-4-31b-it:free",
        "minimax/minimax-m3:free",
        "nvidia/nemotron-3.5-lightning:free",
        "openrouter/auto"
    ]
    for model in models_to_try:
        try:
            resp = _requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={"model": model,
                      "messages": [{"role": "system", "content": system_msg},
                                   {"role": "user",   "content": user_msg}],
                      "temperature": 0.2, "max_tokens": 700},
                timeout=(4.0, 20.0)
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()[:1500]
        except Exception:
            continue
    return _heuristic_symptom_guidance(symptoms)


def _heuristic_symptom_guidance(symptoms: str) -> str:
    """Deterministic clinical heuristic fallback when AI is offline."""
    s = symptoms.lower()
    is_fever  = any(w in s for w in ["fever", "chills", "shivering", "temp"])
    is_dengue = any(w in s for w in ["eye pain", "bone", "joint", "rash", "platelet", "dengue"])
    is_gi     = any(w in s for w in ["nausea", "vomit", "stomach", "jaundice", "stool", "diarrhea"])
    is_anemia = any(w in s for w in ["fatigue", "tired", "weak", "pale", "dizzy", "breathless"])
    is_resp   = any(w in s for w in ["cough", "throat", "breath", "chest", "cold", "flu"])

    if is_dengue or (is_fever and any(w in s for w in ["headache", "muscle", "joint"])):
        return (
            "Possible Conditions:\n"
            "- Viral Febrile Illness (possible Dengue/Arboviral pattern)\n"
            "- Systemic Viral Infection\n\n"
            "Immediate Care Steps:\n"
            "- Avoid Aspirin/Ibuprofen; use only paracetamol for fever\n"
            "- Maintain oral hydration 2.5-3L fluids daily\n"
            "- Track temperature twice daily\n\n"
            "Home Care Tips:\n"
            "- Coconut water, ORS, and fresh fruit juices\n"
            "- Tepid sponging if fever exceeds 101F\n"
            "- Strict bed rest during acute phase\n\n"
            "Suggested Tests:\n"
            "- CBC with Platelet Count and Hematocrit\n"
            "- Dengue NS1 Antigen plus IgM/IgG Serology\n\n"
            "When to Seek Emergency Care:\n"
            "- Persistent vomiting more than 3 times per 24h or severe abdominal pain\n"
            "- Spontaneous bleeding, extreme lethargy, or cold extremities"
        )
    elif is_gi:
        return (
            "Possible Conditions:\n"
            "- Acute Hepatobiliary Strain or Viral Hepatitis pattern\n"
            "- Acute Gastroenteritis\n\n"
            "Immediate Care Steps:\n"
            "- Avoid alcohol, fatty foods, and OTC painkillers\n"
            "- Boiled or filtered water only\n"
            "- Small frequent fluid sips (coconut water, ORS)\n\n"
            "Home Care Tips:\n"
            "- BRAT diet: Banana, Rice, Applesauce, Toast\n"
            "- Rest with upper body slightly elevated\n"
            "- Avoid heavy spices and oils\n\n"
            "Suggested Tests:\n"
            "- Liver Function Test (LFT): Bilirubin, ALT, AST\n"
            "- Abdominal Ultrasound (USG)\n\n"
            "When to Seek Emergency Care:\n"
            "- Deep jaundice with disorientation or extreme drowsiness\n"
            "- Unable to retain any fluids for more than 24 hours"
        )
    elif is_anemia:
        return (
            "Possible Conditions:\n"
            "- Iron Deficiency or Nutritional Anemia pattern\n"
            "- Possible Hypothyroid or B12 deficiency\n\n"
            "Immediate Care Steps:\n"
            "- Avoid sudden strenuous exertion\n"
            "- Rise slowly from sitting or lying positions\n"
            "- Do not start iron supplements without a lab test\n\n"
            "Home Care Tips:\n"
            "- Iron-rich foods: spinach, pomegranate, legumes\n"
            "- Pair with Vitamin C (citrus) to boost absorption\n"
            "- Avoid tea or coffee immediately with meals\n\n"
            "Suggested Tests:\n"
            "- CBC with RBC Indices (Hb, MCV, MCH)\n"
            "- Serum Ferritin and Iron Studies\n\n"
            "When to Seek Emergency Care:\n"
            "- Chest pain or severe shortness of breath\n"
            "- Fainting episodes or signs of active bleeding"
        )
    elif is_resp:
        return (
            "Possible Conditions:\n"
            "- Acute Upper Respiratory Tract Infection (URTI)\n"
            "- Viral Bronchitis or Pharyngitis\n\n"
            "Immediate Care Steps:\n"
            "- Adequate rest and avoid exposure to cold air\n"
            "- Warm saline gargles three times daily for throat relief\n"
            "- Avoid self-prescribing antibiotics without a prescription\n\n"
            "Home Care Tips:\n"
            "- Honey-ginger-lemon in warm water for soothing the throat\n"
            "- Steam inhalation to clear nasal congestion\n"
            "- 2L plus warm fluids daily\n\n"
            "Suggested Tests:\n"
            "- Complete Blood Count (CBC) to check for bacterial infection\n"
            "- Throat Swab Culture if persistent\n\n"
            "When to Seek Emergency Care:\n"
            "- Difficulty breathing, chest tightness, or coughing blood\n"
            "- High fever persisting more than 5 days without improvement"
        )
    else:
        return (
            "Possible Conditions:\n"
            "- General acute symptom syndrome requiring evaluation\n"
            "- Possible metabolic or immune response\n\n"
            "Immediate Care Steps:\n"
            "- Schedule a clinical consultation promptly\n"
            "- Avoid self-medication or unsupervised antibiotics\n"
            "- Keep a daily symptom journal\n\n"
            "Home Care Tips:\n"
            "- 2L plus clean fluids daily\n"
            "- Balanced whole-food nutrition\n"
            "- 7 to 8 hours of restorative sleep\n\n"
            "Suggested Tests:\n"
            "- Complete Blood Count (CBC)\n"
            "- Comprehensive Metabolic Panel\n\n"
            "When to Seek Emergency Care:\n"
            "- Sudden severe chest pressure or difficulty breathing\n"
            "- High fever with neck stiffness or confusion"
        )


# ─── Formatters ──────────────────────────────────────────────────────────────
def format_reports_for_whatsapp(reports: List[Dict]) -> str:
    if not reports:
        return "No laboratory reports found in your record."
    lines = ["Your Lab Reports:"]
    for i, r in enumerate(reports[:5], 1):
        rid  = r.get("report_id", "-")
        cat  = r.get("test_category", "-").title()
        st   = r.get("status", "-")
        date = str(r.get("created_at", "-"))[:10]
        lines.append(f"{i}. {cat} | {rid} | {date} | {st}")
    if len(reports) > 5:
        lines.append(f"... and {len(reports) - 5} more. Visit MEDLENS portal for full history.")
    lines.append("\nType 5 for your latest ML prediction, or 'menu' to go back.")
    return "\n".join(lines)


def format_ml_prediction_for_whatsapp(pred: Dict) -> str:
    disease    = pred.get("disease", "-")
    prediction = pred.get("prediction", "-")
    confidence = pred.get("confidence", 0)
    risk       = pred.get("risk_level", "-")
    model_name = pred.get("model_used", "ML Model")
    date       = str(pred.get("created_at", "-"))[:10]
    conf_pct   = round(float(confidence) * 100) if confidence else 0
    risk_mark  = "HIGH RISK" if "High" in str(risk) else ("MODERATE" if "Moderate" in str(risk) else "LOW RISK")
    return (
        f"MEDLENS ML Prediction Result\n"
        f"Disease Panel: {disease}\n"
        f"Prediction: {prediction}\n"
        f"Confidence: {conf_pct}%\n"
        f"Risk Level: {risk_mark}\n"
        f"Model: {model_name}\n"
        f"Date: {date}\n\n"
        "DISCLAIMER: This is an AI decision-support signal only and does NOT "
        "constitute a medical diagnosis. Please consult your Medicover physician."
    )


def get_doctors_for_whatsapp(query: str = "") -> str:
    doctors_path = Path(__file__).resolve().parent / "medicover_vizag_doctors.json"
    try:
        with open(doctors_path, "r", encoding="utf-8") as f:
            doctors = json.load(f)
    except Exception:
        return "Please visit medicoverhospitals.in/vizag to find our specialists."

    q = query.lower().strip()
    specialty_map = {
        "heart": "Cardiology", "cardiac": "Cardiology",
        "kidney": "Nephrology", "renal": "Nephrology",
        "liver": "Gastroenterology", "stomach": "Gastroenterology",
        "bone": "Orthopedics", "joint": "Orthopedics",
        "thyroid": "Endocrinology", "diabetes": "Endocrinology",
        "blood": "Hematology", "anemia": "Hematology",
        "general": "General Medicine", "fever": "General Medicine",
        "dengue": "General Medicine", "malaria": "General Medicine",
    }
    dept_filter = next((v for k, v in specialty_map.items() if k in q), None)
    filtered = [d for d in doctors if dept_filter and dept_filter.lower() in d.get("department", "").lower()] or doctors

    lines = ["Medicover Vizag Specialists:"]
    seen_depts, count = set(), 0
    for d in filtered:
        if count >= 6:
            break
        dept = d.get("department", "General")
        if dept not in seen_depts or dept_filter:
            seen_depts.add(dept)
            lines.append(f"{d.get('name', 'Unknown')} - {dept}")
            lines.append(f"  {d.get('url', 'https://medicoverhospitals.in')}")
            count += 1

    lines.append("\nBook appointment: 040-68334455")
    lines.append("medicoverhospitals.in/vizag")
    return "\n".join(lines)


# ─── Direct DB Auth Helpers (avoids HTTP self-call deadlock in development) ──
def _direct_db_patient_login(patient_id: str, pin: str) -> Optional[Dict]:
    """Authenticate patient directly against the SQLite DB (no HTTP overhead)."""
    try:
        try:
            from disease_prediction.api import database as db_mod
        except ImportError:
            try:
                from api import database as db_mod
            except ImportError:
                import database as db_mod

        pid = patient_id.strip().upper()
        pin_str = pin.strip()

        candidates = [pin_str, pin_str.upper()]
        if not pin_str.upper().startswith("PIN-"):
            candidates.extend([f"PIN-{pin_str}", f"PIN-{pin_str.upper()}"])
        elif pin_str.upper().startswith("PIN-"):
            candidates.append(pin_str[4:])

        for cand in candidates:
            p = db_mod.authenticate_patient(pid, cand)
            if p:
                import json as _json, time as _time
                payload = {"exp": int(_time.time()) + 86400, "patient_id": pid,
                           "role": "patient", "sub": pid}
                token_data = _json.dumps(payload).encode().hex()
                try:
                    import jwt as _jwt
                    jwt_secret = os.getenv("PATHOLOGY_SECRET_KEY", "") or os.getenv("JWT_SECRET_KEY", "medlens-secret")
                    token_data = _jwt.encode(payload, jwt_secret, algorithm="HS256")
                except Exception:
                    pass
                return {
                    "status": "success",
                    "token": token_data,
                    "patient": p
                }
    except Exception:
        pass
    return None


def _direct_db_get_reports(patient_id: str) -> List[Dict]:
    """Fetch patient reports directly from SQLite DB."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT report_id, patient_id, test_category, status, created_at "
            "FROM lab_reports WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id.upper(),)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _direct_db_get_predictions(patient_id: str) -> Optional[Dict]:
    """Fetch latest ML prediction for patient directly from SQLite DB."""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT disease, prediction, confidence, risk_level, model_used, created_at "
            "FROM ml_predictions WHERE patient_id = ? ORDER BY id DESC LIMIT 1",
            (patient_id.upper(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


# ─── API Bridge Helpers (HTTP fallback for production) ────────────────────────
def patient_login_via_api(patient_id: str, pin: str) -> Optional[Dict]:
    """Authenticate patient: try direct DB first, fall back to HTTP API."""
    # Fast path: direct DB access (no HTTP overhead, no self-referencing)
    result = _direct_db_patient_login(patient_id, pin)
    if result is not None:
        return result
    # Fallback: HTTP API (useful in microservice / cloud split deployments)
    try:
        resp = _requests.post(
            f"{BASE_URL}/api/patient/login",
            json={"patient_id": patient_id.strip().upper(), "access_pin": pin.strip()},
            timeout=5.0
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def get_patient_reports_via_api(token: str, patient_id: str = "") -> List[Dict]:
    """Fetch patient reports: try direct DB first, fall back to HTTP API."""
    if patient_id:
        reports = _direct_db_get_reports(patient_id)
        if reports is not None:
            return reports
    # Fallback: HTTP API
    try:
        resp = _requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def get_latest_ml_prediction(token: str, reports: List[Dict], patient_id: str = "") -> Optional[Dict]:
    """Fetch latest ML prediction: try direct DB first, fall back to HTTP API."""
    if patient_id:
        pred = _direct_db_get_predictions(patient_id)
        if pred is not None:
            return pred
    if not reports:
        return None
    for report in reports:
        rid = report.get("report_id")
        if not rid:
            continue
        try:
            resp = _requests.get(
                f"{BASE_URL}/api/reports/{rid}/predictions",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            if resp.status_code == 200:
                preds = resp.json()
                if preds:
                    return sorted(preds, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        except Exception:
            continue
    return None


# ─── Main Message Handler (State Machine) ────────────────────────────────────
def handle_message(from_number: str, body: str) -> str:
    """
    Central router: receives raw WhatsApp message body, routes through state machine,
    returns plain-text reply (TwiML wrapping done in the FastAPI endpoint).
    """
    msg     = body.strip()
    lower   = msg.lower()
    session = get_session(from_number)
    state   = session["state"]

    # ── Global commands ──────────────────────────────────────────────────────
    if lower in ("reset", "restart", "start over", "main menu", "menu", "home"):
        clear_session(from_number)
        return WELCOME_MSG

    if lower in ("hi", "hello", "hey", "help", "start", "helo", "hii",
                  "good morning", "good evening", "namaste"):
        save_session(from_number, STATE_MENU,
                     session["patient_id"], session["patient_name"], session["data"])
        return WELCOME_MSG

    if lower == "back":
        save_session(from_number, STATE_MENU,
                     session["patient_id"], session["patient_name"], session["data"])
        return MENU_MSG

    # ── STATE: MENU ──────────────────────────────────────────────────────────
    if state == STATE_MENU:
        if lower in ("1", "symptoms", "symptom", "check symptoms", "symptom check"):
            save_session(from_number, STATE_SYMPTOM,
                         session["patient_id"], session["patient_name"], session["data"])
            return SYMPTOM_PROMPT

        elif lower in ("2", "reports", "lab reports", "my reports", "results"):
            if session["patient_id"] and session["data"].get("token"):
                token   = session["data"]["token"]
                pid     = session["patient_id"]
                reports = get_patient_reports_via_api(token, patient_id=pid)
                save_session(from_number, STATE_PATIENT_DASH, session["patient_id"],
                             session["patient_name"], {**session["data"], "reports": reports})
                return format_reports_for_whatsapp(reports)
            else:
                save_session(from_number, STATE_PATIENT_ID, None, None, {"next_action": "reports"})
                return PATIENT_ID_PROMPT

        elif lower in ("3", "emergency", "urgent", "sos", "help me"):
            save_session(from_number, STATE_EMERGENCY,
                         session["patient_id"], session["patient_name"], session["data"])
            return EMERGENCY_PROMPT

        elif lower in ("4", "doctor", "find doctor", "doctors", "specialist"):
            reply = get_doctors_for_whatsapp()
            save_session(from_number, STATE_MENU,
                         session["patient_id"], session["patient_name"], session["data"])
            return reply + "\n\n" + MENU_MSG

        elif lower in ("5", "prediction", "ml", "my prediction", "result", "ml result"):
            if session["patient_id"] and session["data"].get("token"):
                token   = session["data"]["token"]
                pid     = session["patient_id"]
                reports = session["data"].get("reports") or get_patient_reports_via_api(token, patient_id=pid)
                pred    = get_latest_ml_prediction(token, reports, patient_id=pid)
                save_session(from_number, STATE_MENU, session["patient_id"],
                             session["patient_name"], {"token": token})
                reply = (format_ml_prediction_for_whatsapp(pred) if pred
                         else "No ML prediction records found yet. Ask your Medicover doctor "
                              "to run an ML analysis on your report.")
                return reply + "\n\n" + MENU_MSG
            else:
                save_session(from_number, STATE_PATIENT_ID, None, None, {"next_action": "prediction"})
                return PATIENT_ID_PROMPT

        else:
            return "I did not understand that. Please type a number (1-5).\n\n" + MENU_MSG

    # ── STATE: SYMPTOM_INPUT ─────────────────────────────────────────────────
    elif state == STATE_SYMPTOM:
        if len(lower) < 5:
            return "Please describe your symptoms in more detail.\n\n" + SYMPTOM_PROMPT

        triage_level = compute_triage_level(msg)
        if triage_level == "red":
            save_session(from_number, STATE_MENU,
                         session["patient_id"], session["patient_name"], session["data"])
            return (
                "MEDICAL EMERGENCY DETECTED\n\n"
                "CALL 112 IMMEDIATELY!\n\n"
                "Do NOT wait - go to nearest emergency department or call an ambulance NOW.\n\n"
                + MENU_MSG
            )

        header = ("URGENT - Please see a doctor within 24 hours\n\n"
                  if triage_level == "amber"
                  else "LOW URGENCY - Monitor and consult your doctor\n\n")
        guidance = get_ai_symptom_guidance(msg)
        save_session(from_number, STATE_MENU,
                     session["patient_id"], session["patient_name"], session["data"])
        return (
            header
            + "MEDLENS AI Symptom Guidance\n\n"
            + guidance
            + "\n\nAlways consult a qualified physician for proper medical evaluation.\n"
            + "Book at Medicover Vizag: 040-68334455\n\n"
            + MENU_MSG
        )

    # ── STATE: PATIENT_ID_INPUT ──────────────────────────────────────────────
    elif state == STATE_PATIENT_ID:
        clean = msg.upper().strip()
        # If user selected a menu option again (e.g. 1, 2, 3, 4, 5)
        if clean in ("1", "2", "3", "4", "5"):
            save_session(from_number, STATE_MENU, session["patient_id"], session["patient_name"], session["data"])
            return handle_message(from_number, clean)

        if not clean.startswith("PAT-"):
            digits = re.sub(r"[^0-9]", "", clean)
            if digits and len(digits) >= 3:
                clean = f"PAT-{digits}"
            else:
                return "Invalid Patient ID format. Please enter your ID (e.g. PAT-1001).\n\n" + PATIENT_ID_PROMPT
        save_session(from_number, STATE_PIN, None, None, {**session["data"], "patient_id_attempt": clean})
        return f"Patient ID received: {clean}\n\n" + PIN_PROMPT

    # ── STATE: PIN_INPUT ─────────────────────────────────────────────────────
    elif state == STATE_PIN:
        clean = msg.upper().strip()
        # If user pressed a menu number to bail out
        if clean in ("1", "2", "3", "4", "5"):
            save_session(from_number, STATE_MENU, session["patient_id"], session["patient_name"], session["data"])
            return handle_message(from_number, clean)

        pid_attempt = session["data"].get("patient_id_attempt", "")
        pin_attempt = msg.strip()
        if not pin_attempt.upper().startswith("PIN-") and re.fullmatch(r"\d{3,6}", pin_attempt):
            pin_attempt = f"PIN-{pin_attempt}"

        result = patient_login_via_api(pid_attempt, pin_attempt)
        if result:
            patient  = result.get("patient", {})
            token    = result.get("token", "")
            pat_name = patient.get("name", "Patient")
            reports  = get_patient_reports_via_api(token, patient_id=pid_attempt)
            next_act = session["data"].get("next_action", "reports")
            if next_act == "prediction":
                pred = get_latest_ml_prediction(token, reports, patient_id=pid_attempt)
                save_session(from_number, STATE_MENU, pid_attempt, pat_name, {"token": token})
                reply = (format_ml_prediction_for_whatsapp(pred) if pred
                         else "No ML prediction records found yet.")
                return f"Welcome back, {pat_name}!\n\n" + reply + "\n\n" + MENU_MSG
            else:
                save_session(from_number, STATE_MENU, pid_attempt, pat_name,
                             {"token": token, "reports": reports})
                return f"Welcome back, {pat_name}!\n\n" + format_reports_for_whatsapp(reports)
        else:
            save_session(from_number, STATE_PATIENT_ID, None, None,
                         {"next_action": session["data"].get("next_action", "reports")})
            return (
                "Login failed. Patient ID or PIN is incorrect.\n"
                "Demo credentials: ID: PAT-1001, PIN: PIN-1001\n\n"
                + PATIENT_ID_PROMPT
            )

    # ── STATE: PATIENT_DASHBOARD ─────────────────────────────────────────────
    elif state == STATE_PATIENT_DASH:
        save_session(from_number, STATE_MENU,
                     session["patient_id"], session["patient_name"], session["data"])
        return MENU_MSG

    # ── STATE: EMERGENCY_INPUT ───────────────────────────────────────────────
    elif state == STATE_EMERGENCY:
        if len(lower) < 5:
            return "Please describe your emergency in more detail.\n\n" + EMERGENCY_PROMPT

        triage_level = compute_triage_level(msg)
        save_session(from_number, STATE_MENU,
                     session["patient_id"], session["patient_name"], session["data"])
        if triage_level == "red":
            return (
                "CRITICAL EMERGENCY\n\n"
                "CALL 112 IMMEDIATELY!\n"
                "Medicover Emergency: 040-68334455\n\n"
                "Do NOT delay - go to the emergency department NOW.\n\n"
                + MENU_MSG
            )
        guidance = get_ai_symptom_guidance(msg)
        urgency  = ("URGENT - Please see a doctor within 24 hours"
                    if triage_level == "amber"
                    else "LOW URGENCY - Monitor your symptoms")
        return (
            urgency + "\n\n" + guidance
            + "\n\nMedicover Vizag: 040-68334455\n\n"
            + MENU_MSG
        )

    # ── Fallback ─────────────────────────────────────────────────────────────
    else:
        clear_session(from_number)
        return WELCOME_MSG
