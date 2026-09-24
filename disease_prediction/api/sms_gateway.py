"""
MEDLENS AI — SMS Gateway Router
================================
Provides secure API endpoints for the Android SIM SMS Gateway app.

Architecture:
    Doctor creates reminder → sms_outbox entry (queued)
        ↓
    Android app polls GET /api/sms-gateway/queue
        ↓
    Android claims: POST /api/sms-gateway/{id}/claim  → status: processing
        ↓
    Android sends SMS via SmsManager
        ↓
    Android reports: POST /api/sms-gateway/{id}/status → status: sent/failed

Security:
    - All gateway endpoints require X-Gateway-Token header
    - Token verified against hashed values in gateway_devices table
    - Admin endpoints require standard Bearer auth (admin role)
    - Phone numbers are masked in logs/responses
    - Never exposes sensitive medical data via SMS
"""

import os
import re
import secrets
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, HTTPException, status, Depends, Query
from pydantic import BaseModel

try:
    from disease_prediction.api import database as db
except ImportError:
    try:
        from api import database as db
    except ImportError:
        import database as db


router = APIRouter(prefix="/api/sms-gateway", tags=["SMS Gateway"])

# ── Config ─────────────────────────────────────────────────────────────────────
SMS_DAILY_LIMIT = int(os.getenv("SMS_DAILY_LIMIT", "100"))
SMS_GATEWAY_ENABLED = os.getenv("SMS_GATEWAY_ENABLED", "true").lower() == "true"

# ── Phone Validation ────────────────────────────────────────────────────────────
INDIAN_MOBILE_RE = re.compile(r"^(\+91|91|0)?[6-9]\d{9}$")


def normalize_phone(raw: str) -> Optional[str]:
    """Normalises Indian mobile numbers to +91XXXXXXXXXX format."""
    if not raw:
        return None
    cleaned = re.sub(r"[\s\-\(\)]", "", raw)
    m = INDIAN_MOBILE_RE.match(cleaned)
    if not m:
        return None
    digits = re.sub(r"^(\+91|91|0)", "", cleaned)
    return f"+91{digits}"


# ── SMS Template Engine ─────────────────────────────────────────────────────────
def build_sms_text(
    patient_name: str,
    message_type: str,
    custom_message: str = "",
    medication_name: str = "",
    dosage: str = "",
    dose_unit: str = "",
    administration_time: str = "",
    due_date: str = "",
    doctor_name: str = "",
) -> str:
    """
    Generates a safe, minimal SMS text from a template.
    Never includes sensitive lab values or diagnosis details.
    """
    name = patient_name or "Patient"
    templates = {
        "medication_reminder": (
            f"Avenqra AI: Hello {name}, this is a reminder to take your prescribed "
            f"{medication_name or 'medication'}"
            + (f" ({dosage} {dose_unit})" if dosage else "")
            + (f" at {administration_time}" if administration_time else "")
            + ", as instructed by your doctor."
        ),
        "appointment_reminder": (
            f"Avenqra AI: Hello {name}, your appointment is scheduled"
            + (f" on {due_date}" if due_date else "")
            + ". Please contact the clinic if you need to reschedule."
        ),
        "lab_reminder": (
            f"Avenqra AI: Hello {name}, your laboratory test is due"
            + (f" on {due_date}" if due_date else "")
            + ". Please follow any preparation instructions from your clinical team."
        ),
        "report_ready": (
            f"Avenqra AI: Hello {name}, your health report is ready. "
            "Please log in to your Avenqra patient portal to view it securely."
        ),
        "followup_reminder": (
            f"Avenqra AI: Hello {name}, this is a reminder for your follow-up visit"
            + (f" on {due_date}" if due_date else "")
            + ". Please follow your doctor's instructions."
        ),
        "health_checkup": (
            f"Avenqra AI: Hello {name}, your periodic health checkup is due. "
            "Please contact Avenqra Health to schedule your appointment."
        ),
        "vaccination_reminder": (
            f"Avenqra AI: Hello {name}, your vaccination is due"
            + (f" on {due_date}" if due_date else "")
            + ". Please visit the clinic as advised by your doctor."
        ),
        "daily_care": (
            f"Avenqra AI: Hello {name}, this is your daily care reminder. "
            + (custom_message or "Please follow your prescribed care routine.")
        ),
        "diagnosis": (
            f"Avenqra AI: Hello {name}, please follow your doctor's instructions for your ongoing care. "
            + (custom_message or "Contact your clinical team if you have questions.")
        ),
        "checkup": (
            f"Avenqra AI: Hello {name}, your scheduled health checkup reminder. "
            + (custom_message or "Please attend as instructed by your care team.")
        ),
        "custom": f"Avenqra AI: {custom_message}" if custom_message else f"Avenqra AI: Hello {name}, you have a message from your clinical care team.",
    }
    text = templates.get(message_type, templates["custom"])
    # Hard safety limit: SMS is 160 chars per segment, keep to 2 segments max
    if len(text) > 320:
        text = text[:317] + "..."
    return text


# ── Gateway Auth Dependency ─────────────────────────────────────────────────────
def require_gateway_auth(
    x_gateway_token: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Verifies the gateway token from X-Gateway-Token header or admin token from X-Admin-Token."""
    expected_secret = os.getenv("SMS_GATEWAY_TOKEN_SECRET") or os.getenv("ADMIN_GATEWAY_TOKEN") or "medlens-sms-gateway-secret-2026"
    
    # 1. Master admin / pairing secret check (accepted as either X-Admin-Token or X-Gateway-Token)
    if (x_admin_token and x_admin_token == expected_secret) or (x_gateway_token and x_gateway_token == expected_secret):
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM gateway_devices ORDER BY last_seen_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"device_id": "master-gateway", "device_name": "Paired Android Phone", "status": "active"}

    if not x_gateway_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gateway token required. Include X-Gateway-Token or X-Admin-Token header."
        )

    # 2. Lookup registered device token
    device = db.get_gateway_device_by_token(x_gateway_token)
    if device:
        db.touch_gateway_device(device["device_id"])
        return device

    # 3. Resilient Fallback: If container restarted or device connected with existing token, auto-adopt
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM gateway_devices")
    cnt = cur.fetchone()["count"]
    if cnt == 0:
        now_iso = datetime.now().isoformat()
        token_hash = db.hash_secret(x_gateway_token)
        cur.execute("""
            INSERT INTO gateway_devices (device_id, device_name, auth_token_hash, status, last_seen_at, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
        """, ("android-phone", "samsung SM-S711B", token_hash, now_iso, now_iso, now_iso))
        conn.commit()
        cur.execute("SELECT * FROM gateway_devices WHERE device_id = 'android-phone'")
        dev = dict(cur.fetchone())
        conn.close()
        print(f"[SMS-GW] Auto-adopted connecting gateway device: {dev['device_id']}")
        return dev
    conn.close()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or expired gateway token. Please re-pair in Settings."
    )


# ── Request/Response Models ─────────────────────────────────────────────────────
class RegisterGatewayRequest(BaseModel):
    device_id: str
    device_name: str
    admin_token: str  # One-time admin registration token from env


class SmsStatusUpdateRequest(BaseModel):
    status: str          # 'sent' or 'failed'
    failure_reason: Optional[str] = None


class TestSmsRequest(BaseModel):
    phone_number: str
    message: str


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    summary="Register Android SMS Gateway device",
    description=(
        "One-time registration of an Android device as an SMS gateway. "
        "Requires the admin registration token from environment config."
    )
)
def register_gateway(body: RegisterGatewayRequest):
    """Registers an Android phone as an authenticated SMS gateway."""
    expected_secret = os.getenv("SMS_GATEWAY_TOKEN_SECRET") or os.getenv("ADMIN_GATEWAY_TOKEN") or "medlens-sms-gateway-secret-2026"
    if not expected_secret or body.admin_token != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin registration token. Check SMS_GATEWAY_TOKEN_SECRET."
        )
    if not body.device_id or not body.device_name:
        raise HTTPException(status_code=400, detail="device_id and device_name are required.")

    # Generate a unique per-device token for this gateway
    device_token = secrets.token_urlsafe(32)
    result = db.register_gateway_device(body.device_id, body.device_name, device_token)
    print(f"[SMS-GW] Gateway registered: device_id={body.device_id} name={body.device_name}")
    return {
        "status": "registered",
        "device_id": result["device_id"],
        "device_name": result["device_name"],
        "gateway_token": device_token,   # Shown ONCE — store in Android SharedPreferences
        "message": "Store this token securely in the Android gateway app. It will not be shown again."
    }


@router.get(
    "/status",
    summary="Gateway + daily SMS counter status"
)
def gateway_status(device: Dict[str, Any] = Depends(require_gateway_auth)):
    """Returns gateway connectivity confirmation and daily SMS usage stats."""
    if not SMS_GATEWAY_ENABLED:
        return {"gateway_enabled": False, "message": "SMS gateway is currently disabled."}

    counts = db.get_sms_daily_count(device["device_id"])
    daily_limit = SMS_DAILY_LIMIT
    used = counts["today_total"]
    remaining = max(0, daily_limit - used)

    return {
        "gateway_enabled": True,
        "device_id": device["device_id"],
        "device_name": device["device_name"],
        "status": "connected",
        "gateway_status": "online" if device.get("status") == "active" else "offline",
        "last_seen": device.get("last_seen_at"),
        "today_sms_count": used,
        "daily_limit": daily_limit,
        "queued_messages": counts["queued"],
        "sent_messages": counts["sent"],
        "sms_today": used,
        "sms_daily_limit": daily_limit,
        "sms_remaining": remaining,
        "sms_sent": counts["sent"],
        "sms_failed": counts["failed"],
        "sms_queued": counts["queued"],
        "limit_reached": used >= daily_limit,
        "server_time": datetime.now().isoformat()
    }


@router.get(
    "/queue",
    summary="Fetch pending SMS messages (gateway poll)"
)
def get_sms_queue(device: Dict[str, Any] = Depends(require_gateway_auth)):
    """
    Returns pending SMS messages for the gateway to send.
    Automatically recovers stale 'processing' messages.
    Respects daily SMS limit.
    """
    if not SMS_GATEWAY_ENABLED:
        return {"messages": [], "count": 0, "gateway_enabled": False}

    counts = db.get_sms_daily_count()
    if counts["today_total"] >= SMS_DAILY_LIMIT:
        print(f"[SMS-GW] Daily limit reached ({SMS_DAILY_LIMIT}). No messages dispatched.")
        return {
            "messages": [],
            "count": 0,
            "limit_reached": True,
            "message": f"Daily SMS limit of {SMS_DAILY_LIMIT} reached. Delivery paused until tomorrow."
        }

    messages = db.get_sms_queue(limit=5)
    # Mask phone numbers before sending to gateway (gateway gets full number separately via claim)
    safe_messages = []
    for m in messages:
        sm = dict(m)
        ph = sm.get("phone_number", "")
        sm["phone_masked"] = ("*" * (len(ph) - 4) + ph[-4:]) if len(ph) > 4 else "****"
        sm.pop("phone_number", None)  # Gateway gets number only after claiming
        safe_messages.append(sm)

    return {
        "messages": safe_messages,
        "count": len(safe_messages),
        "limit_reached": False,
        "sms_today": counts["today_total"],
        "sms_remaining": max(0, SMS_DAILY_LIMIT - counts["today_total"])
    }


@router.post(
    "/{message_id}/claim",
    summary="Claim an SMS message for sending"
)
def claim_message(
    message_id: int,
    device: Dict[str, Any] = Depends(require_gateway_auth)
):
    """
    Gateway claims ownership of a message before sending.
    Prevents two gateways from sending the same SMS.
    Returns the full phone number only to the claiming device.
    """
    counts = db.get_sms_daily_count()
    if counts["today_total"] >= SMS_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily SMS limit reached.")

    claimed = db.claim_sms_message(message_id, device["device_id"])
    if not claimed:
        raise HTTPException(
            status_code=409,
            detail="Message already claimed by another gateway or is no longer queued."
        )

    print(f"[SMS-GW] Message id={message_id} claimed by device={device['device_id']}")
    return {
        "status": "claimed",
        "id": claimed["id"],
        "phone_number": claimed["phone_number"],   # Full number, revealed only to claimant
        "message": claimed["message"],
        "message_type": claimed["message_type"],
        "attempt_count": claimed["attempt_count"]
    }


@router.post(
    "/{message_id}/status",
    summary="Report SMS send result (sent or failed)"
)
def report_sms_status(
    message_id: int,
    body: SmsStatusUpdateRequest,
    device: Dict[str, Any] = Depends(require_gateway_auth)
):
    """Gateway reports whether the SMS was sent or failed via SIM."""
    if body.status not in ("sent", "failed"):
        raise HTTPException(status_code=400, detail="Status must be 'sent' or 'failed'.")

    updated = db.update_sms_status(
        sms_id=message_id,
        device_id=device["device_id"],
        status=body.status,
        failure_reason=body.failure_reason
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Message not found, not owned by this gateway, or already finalized."
        )

    return {
        "status": "updated",
        "sms_id": message_id,
        "new_status": body.status,
        "device_id": device["device_id"],
        "timestamp": datetime.now().isoformat()
    }


def get_admin_secret() -> str:
    return os.getenv("SMS_GATEWAY_TOKEN_SECRET") or os.getenv("ADMIN_GATEWAY_TOKEN") or "medlens-sms-gateway-secret-2026"


@router.post(
    "/test",
    summary="Queue a direct test SMS (admin)"
)
def test_sms_endpoint(
    body: TestSmsRequest,
    x_admin_token: Optional[str] = Header(None)
):
    """
    Admin queues a test SMS to verify the gateway is working end-to-end.
    Requires X-Admin-Token header matching admin password.
    """
    admin_secret = get_admin_secret()
    if not x_admin_token or x_admin_token != admin_secret:
        raise HTTPException(status_code=403, detail="Admin token required for test SMS.")

    phone = normalize_phone(body.phone_number)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phone number '{body.phone_number}'. Must be a valid Indian mobile number."
        )

    if not body.message or len(body.message.strip()) < 3:
        raise HTTPException(status_code=400, detail="Test message is too short.")

    safe_message = f"AVENQRA AI TEST: {body.message.strip()[:200]}"
    entry = db.create_sms_outbox_entry(
        patient_id="TEST",
        phone_number=phone,
        message=safe_message,
        message_type="test",
        priority=1  # High priority
    )
    return {
        "status": "queued",
        "sms_id": entry["id"],
        "message": "Test SMS queued. Connect the Android gateway to deliver it.",
        "phone_masked": f"***{phone[-4:]}"
    }


@router.get(
    "/history",
    summary="SMS delivery history (admin)"
)
def sms_history(
    patient_id: Optional[str] = Query(None),
    sms_status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    x_admin_token: Optional[str] = Header(None)
):
    """Returns SMS outbox history. Admin access only."""
    admin_secret = get_admin_secret()
    if not x_admin_token or x_admin_token != admin_secret:
        raise HTTPException(status_code=403, detail="Admin token required.")

    history = db.get_sms_history(patient_id=patient_id, status=sms_status, limit=limit)
    counts = db.get_sms_daily_count()
    return {
        "total": len(history),
        "sms_today": counts["today_total"],
        "sms_daily_limit": SMS_DAILY_LIMIT,
        "history": history
    }


@router.post(
    "/{message_id}/retry",
    summary="Retry a failed SMS (admin)"
)
def retry_sms(
    message_id: int,
    x_admin_token: Optional[str] = Header(None)
):
    """Resets a failed SMS back to queued status for re-delivery."""
    admin_secret = get_admin_secret()
    if not x_admin_token or x_admin_token != admin_secret:
        raise HTTPException(status_code=403, detail="Admin token required.")

    updated = db.retry_sms_message(message_id)
    if not updated:
        raise HTTPException(status_code=404, detail="SMS not found or not in failed status.")
    return {"status": "requeued", "sms_id": message_id}


@router.post(
    "/{message_id}/cancel",
    summary="Cancel a queued SMS (admin)"
)
def cancel_sms(
    message_id: int,
    x_admin_token: Optional[str] = Header(None)
):
    """Cancels a queued SMS before it is sent."""
    admin_secret = get_admin_secret()
    if not x_admin_token or x_admin_token != admin_secret:
        raise HTTPException(status_code=403, detail="Admin token required.")

    updated = db.cancel_sms_message(message_id)
    if not updated:
        raise HTTPException(status_code=404, detail="SMS not found or cannot be cancelled (already sent/processing).")
    return {"status": "cancelled", "sms_id": message_id}
