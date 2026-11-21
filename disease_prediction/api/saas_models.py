"""
Pydantic Schemas for Multi-Tenant Healthcare SaaS Platform
MedLens AI / Avenqra AI
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# --- Tenant & Organization Models ---
class TenantCreate(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=150)
    organization_type: str = Field(default="hospital") # hospital, clinic, diagnostic_center
    registration_number: Optional[str] = None
    email: str = Field(..., min_length=5)
    phone: str = Field(..., min_length=8)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    admin_name: str = Field(..., min_length=2)
    admin_username: str = Field(..., min_length=3)
    admin_password: str = Field(..., min_length=6)
    subscription_plan: str = Field(default="starter") # starter, professional, enterprise

class TenantResponse(BaseModel):
    tenant_id: str
    organization_name: str
    organization_type: str
    registration_number: Optional[str] = None
    email: str
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    subscription_plan: str
    subscription_status: str
    trial_ends_at: Optional[str] = None
    current_period_end: Optional[str] = None
    created_at: str
    updated_at: str

class TenantUpdate(BaseModel):
    organization_name: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None

# --- Subscription & Plan Models ---
class PlanInfo(BaseModel):
    plan_id: str
    name: str
    description: str
    price_inr_monthly: float
    price_inr_annual: float
    max_staff: int
    max_patients_per_month: int
    max_ai_queries_per_month: int
    max_report_analyses_per_month: int
    features: List[str]

class PlanUpgradeRequest(BaseModel):
    new_plan_id: str
    billing_cycle: str = "monthly" # monthly, annual
    payment_method: Optional[str] = "razorpay_test"

class UsageStats(BaseModel):
    tenant_id: str
    period_month: str
    plan_id: str
    staff_count: int
    max_staff: int
    patient_records_count: int
    max_patient_records: int
    ai_queries_count: int
    max_ai_queries: int
    report_analyses_count: int
    max_report_analyses: int
    usage_pct_ai: float
    usage_pct_reports: float
    is_limit_approaching: bool
    is_limit_reached: bool

# --- Staff & Invitation Models ---
class StaffInviteRequest(BaseModel):
    email: str
    full_name: str
    role: str # owner, admin, doctor, receptionist, lab_technician, ward_manager, operations_manager
    department: Optional[str] = "General"
    doctor_registration_number: Optional[str] = None

class StaffInviteAccept(BaseModel):
    token: str
    username: str
    password: str
    full_name: Optional[str] = None

class StaffMember(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    doctor_registration_number: Optional[str] = None
    status: str
    created_at: str

# --- Patient Account & Multi-Hospital Linking Models ---
class PatientAccountRegister(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = "Other"
    blood_group: Optional[str] = None
    dpdp_consent: bool = True

class PatientAccountLogin(BaseModel):
    login_identifier: str # email or phone
    password: str

class PatientLinkHospitalRequest(BaseModel):
    tenant_id: str
    hospital_patient_id: str # e.g. PAT-1001
    verification_pin: str # 4-digit PIN matching patient record in hospital
    consent_given: bool = True

class PatientLinkedHospital(BaseModel):
    tenant_id: str
    organization_name: str
    organization_type: str
    hospital_patient_id: str
    verified: bool
    linked_at: str
    patient_name_in_hospital: str

# --- Hospital Login (Combined Doctor/Staff) ---
class HospitalStaffLogin(BaseModel):
    tenant_id: Optional[str] = None # Optional; if omitted, deduced from username or default
    username_or_email: str
    password: str

# --- Platform Owner Models ---
class PlatformMetrics(BaseModel):
    total_organizations: int
    active_organizations: int
    trial_organizations: int
    suspended_organizations: int
    total_staff_users: int
    total_patients_platform: int
    total_ai_queries_all_time: int
    mrr_inr: float
    arr_inr: float
    system_status: str

# --- Payment & Webhook Models ---
class PaymentOrderCreate(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str

# --- Audit Log Models ---
class AuditLogEntry(BaseModel):
    id: int
    tenant_id: Optional[str]
    user_id: Optional[str]
    user_role: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: str
