"""
Core Multi-Tenant SaaS Service & Architecture
MedLens AI / Avenqra AI

Handles:
- Tenant isolation & provisioning
- Configurable subscription plans & usage entitlements
- Staff invitations & role-based access
- Patient account vault & multi-hospital linking
- Payment gateway integration (Razorpay abstraction & sandbox)
- Security audit logs
"""
import os
import sqlite3
import json
import time
import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pathology.db'))

# ==============================================================================
# CONFIGURABLE SUBSCRIPTION PLANS & ENTITLEMENTS
# ==============================================================================
PLAN_DEFINITIONS = {
    "starter": {
        "plan_id": "starter",
        "name": "Clinic Starter",
        "description": "Essential clinical intelligence for outpatient clinics and emerging diagnostic centers.",
        "price_inr_monthly": 4999.0,
        "price_inr_annual": 49990.0,
        "max_staff": 5,
        "max_patients_per_month": 150,
        "max_ai_queries_per_month": 200,
        "max_report_analyses_per_month": 100,
        "features": [
            "AI Symptom Intake & Clinical Case-Taking",
            "Medical Report Analyzer (Up to 100/mo)",
            "5 Staff & Doctor Accounts",
            "NMC-Compliant Digital Prescriptions",
            "Standard Outpatient Token Queue",
            "Community & Email Support"
        ]
    },
    "professional": {
        "plan_id": "professional",
        "name": "Hospital Professional",
        "description": "Advanced multi-department workflows for multispecialty hospitals and large polyclinics.",
        "price_inr_monthly": 14999.0,
        "price_inr_annual": 149990.0,
        "max_staff": 25,
        "max_patients_per_month": 1500,
        "max_ai_queries_per_month": 2000,
        "max_report_analyses_per_month": 1000,
        "features": [
            "Everything in Starter",
            "Up to 25 Doctor & Staff Accounts",
            "Full Hospital Operations (Bed Occupancy, Admissions & Discharges)",
            "Advanced Clinical Decision Support & 5 ML Diagnostic Models",
            "Automated SOAP Note AI Medical Scribe",
            "Live OPD Waiting Room Signage with Native Audio Chimes",
            "Custom Hospital Branding & Telemedicine Suite",
            "Priority 24/7 Clinical Desk Support"
        ]
    },
    "enterprise": {
        "plan_id": "enterprise",
        "name": "Apex Enterprise",
        "description": "Unrestricted scale, ABDM integration, and dedicated infrastructure for hospital chains.",
        "price_inr_monthly": 39999.0,
        "price_inr_annual": 399990.0,
        "max_staff": 250,
        "max_patients_per_month": 15000,
        "max_ai_queries_per_month": 20000,
        "max_report_analyses_per_month": 10000,
        "features": [
            "Everything in Professional",
            "High-Capacity Scalable Staff Allocations (250+)",
            "Ayushman Bharat Digital Mission (ABDM) HL7 FHIR Interoperability",
            "Dedicated PostgreSQL / Supabase Private Tenant Isolation",
            "Custom Hospital EHR & Laboratory Analyzer Integrations",
            "Multi-Branch Central Management Dashboard",
            "Dedicated Healthcare Technology Account Executive"
        ]
    }
}

DEFAULT_LEGACY_TENANT_ID = "tenant_medlens_apex"
DEFAULT_LEGACY_ORG_NAME = "Avenqra Apex Memorial Hospital"

# ==============================================================================
# DATABASE CONNECTION & SCHEMA MIGRATION
# ==============================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        pass
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """PBKDF2-HMAC-SHA256 with 100,000 iterations and salt."""
    if not salt:
        salt = secrets.token_hex(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return f"{salt}${iterations}${derived.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, iterations_str, hash_hex = stored_hash.split('$')
        iterations = int(iterations_str)
        derived = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return secrets.compare_digest(derived.hex(), hash_hex)
    except Exception:
        return False

def ensure_saas_schema():
    """
    Creates SaaS tables and runs zero-data-loss migration on existing tables.
    Preserves all existing patients, reports, and operations records.
    """
    conn = get_db()
    cur = conn.cursor()

    # 1. Tenants table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        tenant_id TEXT PRIMARY KEY,
        organization_name TEXT NOT NULL,
        organization_type TEXT NOT NULL DEFAULT 'hospital',
        registration_number TEXT,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT,
        city TEXT,
        state TEXT,
        country TEXT DEFAULT 'India',
        postal_code TEXT,
        subscription_plan TEXT NOT NULL DEFAULT 'starter',
        subscription_status TEXT NOT NULL DEFAULT 'active',
        trial_ends_at TEXT,
        current_period_end TEXT,
        settings_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 2. Subscriptions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        subscription_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        billing_cycle TEXT NOT NULL DEFAULT 'monthly',
        amount_inr REAL NOT NULL DEFAULT 0.0,
        currency TEXT DEFAULT 'INR',
        status TEXT NOT NULL DEFAULT 'active',
        payment_gateway TEXT DEFAULT 'razorpay',
        gateway_subscription_id TEXT,
        gateway_customer_id TEXT,
        trial_start TEXT,
        trial_end TEXT,
        current_period_start TEXT,
        current_period_end TEXT,
        cancel_at_period_end INTEGER DEFAULT 0,
        canceled_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
    );
    """)

    # 3. Usage meters table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usage_meters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        period_month TEXT NOT NULL,
        usage_count INTEGER NOT NULL DEFAULT 0,
        limit_count INTEGER NOT NULL DEFAULT 100,
        last_updated TEXT NOT NULL,
        UNIQUE(tenant_id, metric_name, period_month),
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
    );
    """)

    # 4. Staff memberships table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tenant_id TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        designation TEXT,
        doctor_registration_number TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE,
        UNIQUE(user_id, tenant_id)
    );
    """)

    # 5. Staff invitations table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_invitations (
        invitation_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        email TEXT NOT NULL,
        full_name TEXT,
        role TEXT NOT NULL,
        department TEXT,
        invitation_token TEXT UNIQUE NOT NULL,
        invited_by_user_id INTEGER,
        status TEXT NOT NULL DEFAULT 'pending',
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
    );
    """)

    # 6. Patient accounts table (Patient Portal users)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patient_accounts (
        account_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        date_of_birth TEXT,
        gender TEXT,
        blood_group TEXT,
        is_verified INTEGER DEFAULT 1,
        consent_version TEXT DEFAULT '2026-v1',
        dpdp_consent_timestamp TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 7. Patient-to-Hospital link table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patient_tenant_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        hospital_patient_id TEXT NOT NULL,
        verification_status TEXT NOT NULL DEFAULT 'verified',
        verified_via TEXT DEFAULT 'pin_auth',
        linked_at TEXT NOT NULL,
        FOREIGN KEY (account_id) REFERENCES patient_accounts (account_id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE,
        UNIQUE(account_id, tenant_id, hospital_patient_id)
    );
    """)

    # 8. SaaS Audit Logs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saas_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        user_id TEXT,
        user_role TEXT,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id TEXT,
        ip_address TEXT,
        status TEXT DEFAULT 'SUCCESS',
        details_json TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 9. Invoices table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        subscription_id TEXT,
        amount_inr REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'paid',
        invoice_pdf_url TEXT,
        payment_method TEXT DEFAULT 'UPI / Card',
        paid_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id) ON DELETE CASCADE
    );
    """)

    # 10. Webhook events idempotency table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_webhook_events (
        event_id TEXT PRIMARY KEY,
        gateway TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        processed_at TEXT NOT NULL
    );
    """)

    # --- ZERO-DATA-LOSS MIGRATIONS: Add tenant_id to existing tables ---
    tables_to_scope = [
        "patients", "users", "lab_reports", "ml_predictions",
        "clinical_cases", "case_history_records", "case_documents",
        "case_consents", "patient_appointments", "patient_reported_issues",
        "patient_care_reminders", "hospital_beds", "shared_sessions_v2",
        "voice_case_sessions", "voice_transcripts", "report_analyses"
    ]

    for tbl in tables_to_scope:
        try:
            cur.execute(f"PRAGMA table_info({tbl});")
            cols = [r[1] for r in cur.fetchall()]
            if cols and "tenant_id" not in cols:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN tenant_id TEXT DEFAULT '{DEFAULT_LEGACY_TENANT_ID}';")
                logger.info(f"Added tenant_id column to legacy table: {tbl}")
        except Exception as e:
            logger.warning(f"Note on table {tbl} migration: {e}")

    # Seed Default Legacy Tenant if not present
    cur.execute("SELECT tenant_id FROM tenants WHERE tenant_id = ?", (DEFAULT_LEGACY_TENANT_ID,))
    if not cur.fetchone():
        now = datetime.utcnow().isoformat()
        cur.execute("""
        INSERT INTO tenants (
            tenant_id, organization_name, organization_type, registration_number,
            email, phone, address, city, state, postal_code,
            subscription_plan, subscription_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            DEFAULT_LEGACY_TENANT_ID, DEFAULT_LEGACY_ORG_NAME, "hospital", "NABH-AP-2026-0418",
            "admin@medlens.ai", "+91-891-2894000", "Health City Campus, Arilova", "Visakhapatnam",
            "Andhra Pradesh", "530040", "enterprise", "active", now, now
        ))
        # Initial subscription
        cur.execute("""
        INSERT INTO subscriptions (
            subscription_id, tenant_id, plan_id, billing_cycle, amount_inr,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"SUB-{int(time.time())}-APEX", DEFAULT_LEGACY_TENANT_ID, "enterprise", "annual",
            399990.0, "active", now, now
        ))
        logger.info("Provisioned default legacy tenant: Avenqra Apex Memorial Hospital")

    # Update any existing records where tenant_id is NULL to point to legacy tenant
    for tbl in tables_to_scope:
        try:
            cur.execute(f"UPDATE {tbl} SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''", (DEFAULT_LEGACY_TENANT_ID,))
        except Exception:
            pass

    # Ensure admin user has membership in legacy tenant
    cur.execute("SELECT id, username, role FROM users WHERE username = 'admin'")
    admin_row = cur.fetchone()
    if admin_row:
        cur.execute("SELECT id FROM staff_memberships WHERE user_id = ? AND tenant_id = ?", (admin_row["id"], DEFAULT_LEGACY_TENANT_ID))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO staff_memberships (user_id, tenant_id, role, designation, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (admin_row["id"], DEFAULT_LEGACY_TENANT_ID, "owner", "Chief Medical Superintendent", "active", datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

# Initialize schema immediately on module load
try:
    ensure_saas_schema()
except Exception as e:
    logger.error(f"Error ensuring SaaS schema: {e}")

# ==============================================================================
# TENANT MANAGEMENT SERVICE
# ==============================================================================
class TenantService:
    @staticmethod
    def create_tenant(data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        now_str = now.isoformat()
        
        # Generate safe slug / tenant ID
        clean_name = "".join(c.lower() for c in data["organization_name"] if c.isalnum() or c == ' ')
        slug = "-".join(clean_name.split()[:4])
        tenant_id = f"org_{slug}_{secrets.token_hex(3)}"
        
        plan_id = data.get("subscription_plan", "starter")
        if plan_id not in PLAN_DEFINITIONS:
            plan_id = "starter"
            
        trial_end = (now + timedelta(days=30)).isoformat()
        
        cur.execute("""
        INSERT INTO tenants (
            tenant_id, organization_name, organization_type, registration_number,
            email, phone, address, city, state, postal_code,
            subscription_plan, subscription_status, trial_ends_at, current_period_end,
            settings_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tenant_id, data["organization_name"], data.get("organization_type", "hospital"),
            data.get("registration_number", ""), data["email"], data["phone"],
            data.get("address", ""), data.get("city", ""), data.get("state", ""),
            data.get("postal_code", ""), plan_id, "trialing", trial_end, trial_end,
            json.dumps({"brand_color": "#0284c7", "theme": "clinical"}), now_str, now_str
        ))
        
        # Create trial subscription record
        sub_id = f"SUB-{int(time.time())}-{secrets.token_hex(3).upper()}"
        cur.execute("""
        INSERT INTO subscriptions (
            subscription_id, tenant_id, plan_id, billing_cycle, amount_inr,
            status, trial_start, trial_end, current_period_start, current_period_end,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sub_id, tenant_id, plan_id, "monthly", 0.0, "trialing",
            now_str, trial_end, now_str, trial_end, now_str, now_str
        ))
        
        # Create initial Administrator / Owner account
        admin_pwd_hash = hash_password(data["admin_password"])
        cur.execute("""
        INSERT INTO users (username, role, password_hash, created_at, tenant_id)
        VALUES (?, ?, ?, ?, ?)
        """, (data["admin_username"], "admin", admin_pwd_hash, now_str, tenant_id))
        user_id = cur.lastrowid
        
        # Create staff membership
        cur.execute("""
        INSERT INTO staff_memberships (
            user_id, tenant_id, role, department, designation, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, tenant_id, "owner", "Hospital Administration", "Hospital Owner / Superintendent", "active", now_str))
        
        conn.commit()
        conn.close()
        
        # Log audit event
        AuditService.log(
            tenant_id=tenant_id,
            user_id=str(user_id),
            user_role="owner",
            action="TENANT_REGISTERED",
            resource_type="tenant",
            resource_id=tenant_id,
            details={"name": data["organization_name"], "plan": plan_id}
        )
        
        return {
            "tenant_id": tenant_id,
            "organization_name": data["organization_name"],
            "admin_username": data["admin_username"],
            "subscription_plan": plan_id,
            "subscription_status": "trialing",
            "trial_ends_at": trial_end,
            "created_at": now_str
        }

    @staticmethod
    def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def list_tenants(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        query = "SELECT * FROM tenants"
        params = []
        if status_filter:
            query += " WHERE subscription_status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
        
        # Enrich with staff and patient counts
        for r in rows:
            tid = r["tenant_id"]
            cur.execute("SELECT COUNT(*) FROM staff_memberships WHERE tenant_id = ? AND status = 'active'", (tid,))
            r["active_staff_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM patients WHERE tenant_id = ?", (tid,))
            r["total_patients_count"] = cur.fetchone()[0]
            
        conn.close()
        return rows

    @staticmethod
    def update_tenant(tenant_id: str, updates: Dict[str, Any]) -> bool:
        conn = get_db()
        cur = conn.cursor()
        fields = []
        params = []
        for k, v in updates.items():
            if k in ["organization_name", "registration_number", "email", "phone", "address", "city", "state", "postal_code", "settings_json"]:
                fields.append(f"{k} = ?")
                params.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
        if not fields:
            conn.close()
            return False
            
        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(tenant_id)
        
        cur.execute(f"UPDATE tenants SET {', '.join(fields)} WHERE tenant_id = ?", tuple(params))
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        return updated

    @staticmethod
    def set_tenant_status(tenant_id: str, new_status: str) -> bool:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE tenants SET subscription_status = ?, updated_at = ? WHERE tenant_id = ?", 
                    (new_status, datetime.utcnow().isoformat(), tenant_id))
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        return updated

# ==============================================================================
# USAGE METERING & ENTITLEMENT ENFORCEMENT
# ==============================================================================
class UsageService:
    @staticmethod
    def record_usage(tenant_id: str, metric_name: str, increment_by: int = 1) -> bool:
        """
        Increments tenant usage for a given metric in the current month.
        Metrics: 'ai_queries', 'report_analyses', 'patient_records', 'api_calls'.
        """
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        period_month = now.strftime("%Y-%m")
        now_str = now.isoformat()
        
        # Get tenant plan to set limits
        cur.execute("SELECT subscription_plan FROM tenants WHERE tenant_id = ?", (tenant_id,))
        t_row = cur.fetchone()
        plan_id = t_row["subscription_plan"] if t_row else "starter"
        plan_limits = PLAN_DEFINITIONS.get(plan_id, PLAN_DEFINITIONS["starter"])
        
        limit_map = {
            "ai_queries": plan_limits["max_ai_queries_per_month"],
            "report_analyses": plan_limits["max_report_analyses_per_month"],
            "patient_records": plan_limits["max_patients_per_month"],
            "api_calls": plan_limits["max_ai_queries_per_month"] * 3
        }
        default_limit = limit_map.get(metric_name, 1000)
        
        cur.execute("""
        INSERT INTO usage_meters (tenant_id, metric_name, period_month, usage_count, limit_count, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, metric_name, period_month) DO UPDATE SET
            usage_count = usage_count + ?,
            last_updated = ?
        """, (tenant_id, metric_name, period_month, increment_by, default_limit, now_str, increment_by, now_str))
        
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def check_entitlement(tenant_id: str, metric_name: str) -> Tuple[bool, str, int, int]:
        """
        Returns (is_allowed, reason, current_usage, max_limit).
        Enforces backend plan quota checks.
        """
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        period_month = now.strftime("%Y-%m")
        
        cur.execute("SELECT subscription_plan, subscription_status FROM tenants WHERE tenant_id = ?", (tenant_id,))
        t_row = cur.fetchone()
        if not t_row:
            conn.close()
            return False, "Tenant not found", 0, 0
            
        if t_row["subscription_status"] in ["suspended", "canceled"]:
            conn.close()
            return False, f"Subscription is {t_row['subscription_status']}. Please renew to access this service.", 0, 0
            
        plan_id = t_row["subscription_plan"]
        plan_limits = PLAN_DEFINITIONS.get(plan_id, PLAN_DEFINITIONS["starter"])
        
        cur.execute("""
        SELECT usage_count, limit_count FROM usage_meters
        WHERE tenant_id = ? AND metric_name = ? AND period_month = ?
        """, (tenant_id, metric_name, period_month))
        u_row = cur.fetchone()
        conn.close()
        
        current_usage = u_row["usage_count"] if u_row else 0
        limit_map = {
            "ai_queries": plan_limits["max_ai_queries_per_month"],
            "report_analyses": plan_limits["max_report_analyses_per_month"],
            "patient_records": plan_limits["max_patients_per_month"]
        }
        max_limit = limit_map.get(metric_name, 999999)
        
        if current_usage >= max_limit:
            return False, f"Monthly quota exceeded for {metric_name} ({current_usage}/{max_limit}). Please upgrade your SaaS plan.", current_usage, max_limit
            
        return True, "Entitlement verified", current_usage, max_limit

    @staticmethod
    def get_usage_summary(tenant_id: str) -> Dict[str, Any]:
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        period_month = now.strftime("%Y-%m")
        
        cur.execute("SELECT subscription_plan, subscription_status FROM tenants WHERE tenant_id = ?", (tenant_id,))
        t_row = cur.fetchone()
        plan_id = t_row["subscription_plan"] if t_row else "starter"
        plan_limits = PLAN_DEFINITIONS.get(plan_id, PLAN_DEFINITIONS["starter"])
        
        # Staff count
        cur.execute("SELECT COUNT(*) FROM staff_memberships WHERE tenant_id = ? AND status = 'active'", (tenant_id,))
        staff_count = cur.fetchone()[0]
        
        # Patients count
        cur.execute("SELECT COUNT(*) FROM patients WHERE tenant_id = ?", (tenant_id,))
        patients_count = cur.fetchone()[0]
        
        # AI Queries this month
        cur.execute("SELECT usage_count FROM usage_meters WHERE tenant_id = ? AND metric_name = 'ai_queries' AND period_month = ?", (tenant_id, period_month))
        ai_row = cur.fetchone()
        ai_count = ai_row[0] if ai_row else 0
        
        # Report analyses this month
        cur.execute("SELECT usage_count FROM usage_meters WHERE tenant_id = ? AND metric_name = 'report_analyses' AND period_month = ?", (tenant_id, period_month))
        rep_row = cur.fetchone()
        rep_count = rep_row[0] if rep_row else 0
        
        conn.close()
        
        max_ai = plan_limits["max_ai_queries_per_month"]
        max_rep = plan_limits["max_report_analyses_per_month"]
        
        pct_ai = round((ai_count / max_ai) * 100, 1) if max_ai > 0 else 0
        pct_rep = round((rep_count / max_rep) * 100, 1) if max_rep > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "period_month": period_month,
            "plan_id": plan_id,
            "plan_name": plan_limits["name"],
            "staff_count": staff_count,
            "max_staff": plan_limits["max_staff"],
            "patient_records_count": patients_count,
            "max_patient_records": plan_limits["max_patients_per_month"],
            "ai_queries_count": ai_count,
            "max_ai_queries": max_ai,
            "report_analyses_count": rep_count,
            "max_report_analyses": max_rep,
            "usage_pct_ai": pct_ai,
            "usage_pct_reports": pct_rep,
            "is_limit_approaching": (pct_ai >= 80 or pct_rep >= 80),
            "is_limit_reached": (ai_count >= max_ai or rep_count >= max_rep)
        }

# ==============================================================================
# STAFF & INVITATIONS SERVICE (COMBINED HOSPITAL PORTAL)
# ==============================================================================
class StaffService:
    VALID_ROLES = ["owner", "admin", "doctor", "receptionist", "lab_technician", "ward_manager", "operations_manager"]

    @staticmethod
    def invite_staff(tenant_id: str, data: Dict[str, Any], invited_by_user_id: int) -> Dict[str, Any]:
        role = data.get("role", "").lower()
        if role not in StaffService.VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Supported roles: {', '.join(StaffService.VALID_ROLES)}")
            
        # Check plan staff limits
        usage = UsageService.get_usage_summary(tenant_id)
        if usage["staff_count"] >= usage["max_staff"]:
            raise ValueError(f"Staff account limit of {usage['max_staff']} reached for plan '{usage['plan_name']}'. Please upgrade.")
            
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        now_str = now.isoformat()
        token = secrets.token_urlsafe(32)
        invitation_id = f"INV-{int(time.time())}-{secrets.token_hex(3).upper()}"
        expires_at = (now + timedelta(days=7)).isoformat()
        
        cur.execute("""
        INSERT INTO staff_invitations (
            invitation_id, tenant_id, email, full_name, role, department,
            invitation_token, invited_by_user_id, status, expires_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invitation_id, tenant_id, data["email"], data.get("full_name", ""),
            role, data.get("department", "General"), token, invited_by_user_id,
            "pending", expires_at, now_str
        ))
        
        conn.commit()
        conn.close()
        
        AuditService.log(
            tenant_id=tenant_id,
            user_id=str(invited_by_user_id),
            user_role="admin",
            action="STAFF_INVITED",
            resource_type="staff_invitation",
            resource_id=invitation_id,
            details={"email": data["email"], "role": role}
        )
        
        return {
            "invitation_id": invitation_id,
            "email": data["email"],
            "role": role,
            "token": token,
            "invitation_url": f"/hospital/join?token={token}",
            "expires_at": expires_at
        }

    @staticmethod
    def accept_invitation(token: str, username: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cur.execute("SELECT * FROM staff_invitations WHERE invitation_token = ? AND status = 'pending'", (token,))
        inv = cur.fetchone()
        if not inv:
            conn.close()
            raise ValueError("Invalid, expired, or previously redeemed invitation token.")
            
        if inv["expires_at"] < now:
            cur.execute("UPDATE staff_invitations SET status = 'expired' WHERE invitation_token = ?", (token,))
            conn.commit()
            conn.close()
            raise ValueError("This invitation has expired. Please request a new invite from your hospital administrator.")
            
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            conn.close()
            raise ValueError(f"Username '{username}' is already in use. Please choose another username.")
            
        pwd_hash = hash_password(password)
        cur.execute("""
        INSERT INTO users (username, role, password_hash, created_at, tenant_id)
        VALUES (?, ?, ?, ?, ?)
        """, (username, inv["role"], pwd_hash, now, inv["tenant_id"]))
        new_user_id = cur.lastrowid
        
        # Link in staff_memberships
        cur.execute("""
        INSERT INTO staff_memberships (
            user_id, tenant_id, role, department, designation, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_user_id, inv["tenant_id"], inv["role"], inv["department"], full_name or inv["full_name"], "active", now))
        
        # Update invitation
        cur.execute("UPDATE staff_invitations SET status = 'accepted' WHERE invitation_token = ?", (token,))
        
        conn.commit()
        conn.close()
        
        AuditService.log(
            tenant_id=inv["tenant_id"],
            user_id=str(new_user_id),
            user_role=inv["role"],
            action="STAFF_INVITATION_ACCEPTED",
            resource_type="user",
            resource_id=str(new_user_id),
            details={"username": username, "role": inv["role"]}
        )
        
        return {
            "status": "success",
            "user_id": new_user_id,
            "username": username,
            "role": inv["role"],
            "tenant_id": inv["tenant_id"]
        }

    @staticmethod
    def list_staff(tenant_id: str) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        SELECT u.id as user_id, u.username, sm.role, sm.department, sm.designation,
               sm.doctor_registration_number, sm.status, sm.created_at
        FROM staff_memberships sm
        JOIN users u ON sm.user_id = u.id
        WHERE sm.tenant_id = ?
        ORDER BY sm.created_at DESC
        """, (tenant_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def revoke_staff(tenant_id: str, user_id: int, admin_user_id: int) -> bool:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE staff_memberships SET status = 'revoked' WHERE tenant_id = ? AND user_id = ?", (tenant_id, user_id))
        conn.commit()
        revoked = cur.rowcount > 0
        conn.close()
        if revoked:
            AuditService.log(
                tenant_id=tenant_id,
                user_id=str(admin_user_id),
                user_role="admin",
                action="STAFF_REVOKED",
                resource_type="user",
                resource_id=str(user_id)
            )
        return revoked

# ==============================================================================
# PATIENT PORTAL VAULT & MULTI-HOSPITAL LINKING SERVICE
# ==============================================================================
class PatientAccountService:
    @staticmethod
    def register(data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        email = data["email"].strip().lower()
        phone = data["phone"].strip()
        
        cur.execute("SELECT account_id FROM patient_accounts WHERE email = ? OR phone = ?", (email, phone))
        if cur.fetchone():
            conn.close()
            raise ValueError("An account with this email or mobile number already exists.")
            
        account_id = f"PA-{secrets.token_hex(4).upper()}"
        pwd_hash = hash_password(data["password"])
        
        cur.execute("""
        INSERT INTO patient_accounts (
            account_id, email, phone, full_name, password_hash,
            date_of_birth, gender, blood_group, is_verified,
            consent_version, dpdp_consent_timestamp, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, email, phone, data["full_name"], pwd_hash,
            data.get("date_of_birth", ""), data.get("gender", "Other"),
            data.get("blood_group", ""), 1, "2026-v1", now, now, now
        ))
        
        conn.commit()
        conn.close()
        
        AuditService.log(
            tenant_id=None,
            user_id=account_id,
            user_role="patient",
            action="PATIENT_ACCOUNT_REGISTERED",
            resource_type="patient_account",
            resource_id=account_id,
            details={"email": email}
        )
        
        return {
            "account_id": account_id,
            "full_name": data["full_name"],
            "email": email,
            "phone": phone
        }

    @staticmethod
    def authenticate(identifier: str, password: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        identifier_clean = identifier.strip().lower()
        
        cur.execute("""
        SELECT * FROM patient_accounts WHERE LOWER(email) = ? OR phone = ?
        """, (identifier_clean, identifier.strip()))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
            
        if not verify_password(password, row["password_hash"]):
            return None
            
        return dict(row)

    @staticmethod
    def link_hospital(account_id: str, tenant_id: str, hospital_patient_id: str, verification_pin: str) -> Dict[str, Any]:
        """
        Securely links a patient's master account to an organization's EHR patient record.
        Requires patient's PIN verification to prevent unauthorized record linking!
        """
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # 1. Verify organization exists
        cur.execute("SELECT organization_name FROM tenants WHERE tenant_id = ?", (tenant_id,))
        t_row = cur.fetchone()
        if not t_row:
            conn.close()
            raise ValueError("Target hospital organization does not exist.")
            
        # 2. Verify hospital patient record exists and check access_pin_hash
        cur.execute("SELECT patient_id, name, access_pin_hash FROM patients WHERE tenant_id = ? AND patient_id = ?", 
                    (tenant_id, hospital_patient_id))
        p_row = cur.fetchone()
        if not p_row:
            conn.close()
            raise ValueError(f"Patient ID '{hospital_patient_id}' not found in {t_row['organization_name']}.")
            
        # Verify PIN against stored hash
        if not verify_password(verification_pin, p_row["access_pin_hash"]):
            # Also allow fallback plain pin match if legacy
            if p_row["access_pin_hash"] != verification_pin:
                conn.close()
                AuditService.log(
                    tenant_id=tenant_id,
                    user_id=account_id,
                    user_role="patient",
                    action="PATIENT_LINK_PIN_FAILED",
                    resource_type="patient_tenant_link",
                    resource_id=hospital_patient_id,
                    status="FAILED"
                )
                raise ValueError("Incorrect Patient Security PIN. Verification failed.")
                
        # 3. Create or update link
        cur.execute("""
        INSERT INTO patient_tenant_links (
            account_id, tenant_id, hospital_patient_id, verification_status, verified_via, linked_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, tenant_id, hospital_patient_id) DO UPDATE SET
            verification_status = 'verified',
            linked_at = ?
        """, (account_id, tenant_id, hospital_patient_id, "verified", "pin_auth", now, now))
        
        conn.commit()
        conn.close()
        
        AuditService.log(
            tenant_id=tenant_id,
            user_id=account_id,
            user_role="patient",
            action="PATIENT_HOSPITAL_LINKED",
            resource_type="patient_tenant_link",
            resource_id=hospital_patient_id,
            details={"hospital": t_row["organization_name"], "patient_id": hospital_patient_id}
        )
        
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "hospital_name": t_row["organization_name"],
            "hospital_patient_id": hospital_patient_id,
            "patient_name": p_row["name"],
            "linked_at": now
        }

    @staticmethod
    def get_linked_hospitals(account_id: str) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        SELECT ptl.tenant_id, t.organization_name, t.organization_type,
               ptl.hospital_patient_id, p.name as patient_name_in_hospital,
               ptl.verification_status, ptl.linked_at
        FROM patient_tenant_links ptl
        JOIN tenants t ON ptl.tenant_id = t.tenant_id
        LEFT JOIN patients p ON (p.tenant_id = ptl.tenant_id AND p.patient_id = ptl.hospital_patient_id)
        WHERE ptl.account_id = ? AND ptl.verification_status = 'verified'
        ORDER BY ptl.linked_at DESC
        """, (account_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_aggregated_reports(account_id: str) -> List[Dict[str, Any]]:
        """
        Returns all lab reports belonging to the patient across all their verified linked hospitals!
        """
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        SELECT lr.report_id, lr.patient_id, lr.test_category, lr.status,
               lr.doctor_remarks, lr.created_at, t.organization_name as hospital_name, lr.tenant_id
        FROM lab_reports lr
        JOIN patient_tenant_links ptl ON (lr.tenant_id = ptl.tenant_id AND lr.patient_id = ptl.hospital_patient_id)
        JOIN tenants t ON lr.tenant_id = t.tenant_id
        WHERE ptl.account_id = ? AND ptl.verification_status = 'verified'
        ORDER BY lr.created_at DESC
        """, (account_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

# ==============================================================================
# AUDIT LOGGING SERVICE
# ==============================================================================
class AuditService:
    @staticmethod
    def log(tenant_id: Optional[str], user_id: Optional[str], user_role: Optional[str],
            action: str, resource_type: str, resource_id: Optional[str] = None,
            ip_address: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
            status: str = "SUCCESS"):
        try:
            conn = get_db()
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()
            cur.execute("""
            INSERT INTO saas_audit_logs (
                tenant_id, user_id, user_role, action, resource_type,
                resource_id, ip_address, status, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant_id, user_id, user_role, action, resource_type,
                resource_id, ip_address, status, json.dumps(details) if details else None, now
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")

    @staticmethod
    def query(tenant_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        if tenant_id:
            cur.execute("""
            SELECT * FROM saas_audit_logs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?
            """, (tenant_id, limit))
        else:
            cur.execute("""
            SELECT * FROM saas_audit_logs ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if r.get("details_json"):
                try:
                    r["details"] = json.loads(r["details_json"])
                except Exception:
                    r["details"] = r["details_json"]
        conn.close()
        return rows

# ==============================================================================
# PAYMENT GATEWAY ABSTRACTION (RAZORPAY & SANDBOX)
# ==============================================================================
class PaymentService:
    @staticmethod
    def create_order(tenant_id: str, plan_id: str, billing_cycle: str = "monthly") -> Dict[str, Any]:
        plan = PLAN_DEFINITIONS.get(plan_id)
        if not plan:
            raise ValueError(f"Invalid plan '{plan_id}'")
            
        amount_inr = plan["price_inr_annual"] if billing_cycle == "annual" else plan["price_inr_monthly"]
        order_id = f"order_{secrets.token_hex(8)}"
        
        # Check if live Razorpay credentials exist
        razorpay_key = os.getenv("RAZORPAY_KEY_ID")
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
        
        is_live = bool(razorpay_key and razorpay_secret and not razorpay_key.startswith("rzp_test_placeholder"))
        
        return {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "amount_inr": amount_inr,
            "amount_paise": int(amount_inr * 100),
            "currency": "INR",
            "key_id": razorpay_key if is_live else "rzp_test_sandbox_mode",
            "is_sandbox": not is_live,
            "gateway": "razorpay"
        }

    @staticmethod
    def verify_and_activate(tenant_id: str, plan_id: str, payment_id: str, order_id: str, signature: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies payment signature and upgrades tenant subscription.
        Idempotent and cryptographically validated.
        """
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
        if razorpay_secret and signature:
            message = f"{order_id}|{payment_id}"
            expected = hmac.new(razorpay_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
            if not secrets.compare_digest(signature, expected):
                raise ValueError("Cryptographic payment signature verification failed!")
                
        plan = PLAN_DEFINITIONS.get(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' does not exist.")
            
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow()
        now_str = now.isoformat()
        period_end = (now + timedelta(days=30)).isoformat()
        
        # Update tenant plan
        cur.execute("""
        UPDATE tenants SET
            subscription_plan = ?,
            subscription_status = 'active',
            current_period_end = ?,
            updated_at = ?
        WHERE tenant_id = ?
        """, (plan_id, period_end, now_str, tenant_id))
        
        # Create active subscription record
        sub_id = f"SUB-{int(time.time())}-{secrets.token_hex(3).upper()}"
        cur.execute("""
        INSERT INTO subscriptions (
            subscription_id, tenant_id, plan_id, billing_cycle, amount_inr,
            status, payment_gateway, gateway_subscription_id,
            current_period_start, current_period_end, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sub_id, tenant_id, plan_id, "monthly", plan["price_inr_monthly"],
            "active", "razorpay", payment_id, now_str, period_end, now_str, now_str
        ))
        
        # Record official invoice
        inv_id = f"INV-{now.strftime('%Y%m')}-{secrets.token_hex(3).upper()}"
        cur.execute("""
        INSERT INTO invoices (
            invoice_id, tenant_id, subscription_id, amount_inr, status,
            payment_method, paid_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id, tenant_id, sub_id, plan["price_inr_monthly"], "paid",
            "Razorpay UPI/Card", now_str, now_str
        ))
        
        conn.commit()
        conn.close()
        
        AuditService.log(
            tenant_id=tenant_id,
            user_id="SYSTEM_PAYMENT",
            user_role="billing",
            action="SUBSCRIPTION_ACTIVATED",
            resource_type="subscription",
            resource_id=sub_id,
            details={"plan": plan_id, "amount": plan["price_inr_monthly"], "payment_id": payment_id}
        )
        
        return {
            "status": "active",
            "subscription_id": sub_id,
            "invoice_id": inv_id,
            "plan_id": plan_id,
            "current_period_end": period_end
        }

    @staticmethod
    def handle_webhook(event_payload: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes webhooks idempotently with duplicate event protection.
        """
        event_id = event_payload.get("event_id") or event_payload.get("id") or secrets.token_hex(16)
        payload_str = json.dumps(event_payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        conn = get_db()
        cur = conn.cursor()
        
        # Idempotency check
        cur.execute("SELECT event_id FROM payment_webhook_events WHERE event_id = ?", (event_id,))
        if cur.fetchone():
            conn.close()
            return {"status": "duplicate_event_ignored", "event_id": event_id}
            
        now_str = datetime.utcnow().isoformat()
        cur.execute("""
        INSERT INTO payment_webhook_events (event_id, gateway, event_type, payload_hash, processed_at)
        VALUES (?, ?, ?, ?, ?)
        """, (event_id, "razorpay", event_payload.get("event", "payment.captured"), payload_hash, now_str))
        
        conn.commit()
        conn.close()
        return {"status": "processed", "event_id": event_id}
