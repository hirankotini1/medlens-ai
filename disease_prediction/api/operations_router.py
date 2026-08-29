"""
FastAPI Router for Hospital Operations Intelligence
"""
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from disease_prediction.hospital_operations.service import HospitalOperationsService

router = APIRouter(prefix="/api/operations", tags=["Hospital Operations"])

# Singleton service instance
_ops_service = HospitalOperationsService()


@router.get("/overview")
def get_operations_overview(force_refresh: bool = False):
    """
    Returns the unified hospital operations overview answering the 4 primary leadership questions:
    1. How many active patients?
    2. How full are the beds?
    3. Are lab tests on time?
    4. What needs attention?
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline(force_refresh=force_refresh)
        return overview.model_dump() if hasattr(overview, 'model_dump') else overview.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate operations overview: {str(e)}")


@router.get("/quality")
def get_data_quality_scorecard():
    """
    Returns transparent data quality score with mathematical penalty breakdown.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        return overview.data_quality.model_dump() if hasattr(overview.data_quality, 'model_dump') else overview.data_quality.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve data quality scorecard: {str(e)}")


@router.get("/sources")
def get_data_sources_stats():
    """
    Returns intake statistics for HIS Admissions, Lab Turnaround, and Manual Bed Occupancy.
    """
    try:
        return _ops_service.get_sources_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve data source stats: {str(e)}")


@router.get("/conflicts")
def get_reconciliation_conflicts(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity (Critical, High, Medium, Low, Info)")
):
    """
    Returns detected cross-source conflicts, applied reconciliation rules, and resolution statuses.
    """
    try:
        return _ops_service.get_conflicts_data(category=category, severity=severity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conflicts: {str(e)}")


@router.get("/conflicts/{conflict_id}")
def get_single_conflict_detail(conflict_id: str):
    """
    Returns deep inspection and 'Why is this different?' explanation for a specific discrepancy.
    """
    try:
        conflict = _ops_service.get_conflict_by_id(conflict_id)
        if not conflict:
            raise HTTPException(status_code=404, detail=f"Conflict ID {conflict_id} not found.")
        return conflict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conflict detail: {str(e)}")


@router.get("/rules")
def get_reconciliation_rules():
    """
    Returns the deterministic reconciliation rules catalog ('How We Resolve Differences').
    """
    try:
        return _ops_service.get_rules_catalog()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reconciliation rules: {str(e)}")


@router.get("/beds")
def get_bed_capacity_metrics(
    warning_threshold: float = 80.0,
    critical_threshold: float = 90.0
):
    """
    Returns ward-by-ward bed availability, occupancy rates, and longitudinal trends.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        data = overview.bed_capacity.model_dump() if hasattr(overview.bed_capacity, 'model_dump') else overview.bed_capacity.dict()
        try:
            live_beds = SupabaseHospitalClient.get_bed_inventory()
            if live_beds:
                live_total = len(live_beds)
                live_occ = sum(1 for b in live_beds if b.get('status') == 'Occupied')
                live_avail = sum(1 for b in live_beds if b.get('status') == 'Available')
                data["live_total_beds"] = live_total
                data["live_occupied_beds"] = live_occ
                data["live_available_beds"] = live_avail
                data["overall"] = {
                    "total": live_total,
                    "occupied": live_occ,
                    "available": live_avail
                }
        except Exception:
            pass
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve bed metrics: {str(e)}")


@router.get("/patient-flow")
def get_patient_flow_metrics():
    """
    Returns admissions, discharges, length of stay, and demographic distributions.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        return overview.patient_flow.model_dump() if hasattr(overview.patient_flow, 'model_dump') else overview.patient_flow.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patient flow metrics: {str(e)}")


@router.get("/lab-performance")
def get_lab_performance_metrics():
    """
    Returns diagnostic turnaround times by priority tier, test name, department, and active pending queue.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        return overview.lab_performance.model_dump() if hasattr(overview.lab_performance, 'model_dump') else overview.lab_performance.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lab metrics: {str(e)}")


@router.get("/alerts")
def get_operational_alerts():
    """
    Returns active operational alerts sorted by severity.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        return [(a.model_dump() if hasattr(a, 'model_dump') else a.dict()) for a in overview.top_alerts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.get("/data-quality")
def get_data_quality_scorecard():
    """
    Returns audit-grade Data Quality Score and transparent deduction methodology.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline()
        return overview.data_quality.model_dump() if hasattr(overview.data_quality, 'model_dump') else overview.data_quality.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve data quality metrics: {str(e)}")


@router.get("/comparison")
def get_source_comparison():
    """
    Returns cross-source comparison matrix (HIS vs BED vs LAB).
    """
    try:
        return _ops_service.get_source_comparison_matrix()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve comparison matrix: {str(e)}")


@router.get("/report/html", response_class=HTMLResponse)
def get_daily_report_html():
    """
    Generates a print-ready, high-resolution HTML daily operations report.
    """
    try:
        return _ops_service.get_daily_report_html()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate HTML report: {str(e)}")


@router.get("/report/csv")
def get_daily_report_csv():
    """
    Generates CSV export of reconciled operational metrics.
    """
    try:
        csv_content = _ops_service.get_daily_report_csv()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=medlens_operations_report.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV export: {str(e)}")


@router.get("/ai-summary")
def get_ai_operations_summary():
    """
    Returns an executive AI brief summarizing reconciled facts with deterministic fallback.
    """
    try:
        return _ops_service.get_ai_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI summary: {str(e)}")


@router.get("/history")
def get_operations_history(limit: int = 20):
    """
    Returns operations reconciliation run history and metric audit trail.
    """
    try:
        return _ops_service.get_operations_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.post("/reconcile")
def trigger_fresh_reconciliation():
    """
    Triggers an on-demand re-ingestion and reconciliation pass across all sources.
    """
    try:
        overview = _ops_service.run_reconciliation_pipeline(force_refresh=True)
        return {
            "status": "success",
            "message": "Hospital Operations reconciliation pipeline completed successfully.",
            "overview": overview.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation trigger failed: {str(e)}")


# =========================================================
# SUPABASE 3-TIER BED MANAGEMENT, ADMISSIONS & STAFF ERP
# =========================================================
import json
import time
import hmac
import hashlib
import secrets
from disease_prediction.hospital_operations.supabase_client import SupabaseHospitalClient
from pydantic import BaseModel
from fastapi import Header, Depends

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "medlens-super-secret-key-vizag-medicover-2026-prod")

def _generate_staff_token(payload: Dict[str, Any], expire_seconds: int = 86400) -> str:
    payload_copy = dict(payload)
    payload_copy['exp'] = int(time.time()) + expire_seconds
    payload_json = json.dumps(payload_copy)
    signature = hmac.new(JWT_SECRET_KEY.encode('utf-8'), payload_json.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload_json.encode('utf-8').hex()}.{signature}"

def get_staff_context(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    try:
        if not token or '.' not in token:
            return None
        parts = token.split('.')
        if len(parts) != 2:
            return None
        payload_hex, signature = parts
        payload_json = bytes.fromhex(payload_hex).decode('utf-8')
        expected_sig = hmac.new(JWT_SECRET_KEY.encode('utf-8'), payload_json.encode('utf-8'), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(payload_json)
        if payload.get('exp', 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def require_staff_role(allowed_roles: List[str]):
    def dependency(auth: Optional[Dict[str, Any]] = Depends(get_staff_context)) -> Dict[str, Any]:
        if not auth or not auth.get('staff_id'):
            raise HTTPException(
                status_code=401,
                detail="Authentication required: Please log in with your Staff Credentials."
            )
        role = auth.get('role')
        if role not in allowed_roles and role != 'OPERATIONS_MANAGER':
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Role '{role}' does not have permission for this operation. Required: {', '.join(allowed_roles)}"
            )
        return auth
    return dependency


class StaffLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login", tags=["Staff Authentication"])
def staff_login(req: StaffLoginRequest):
    """
    Authenticates staff members across the 4 roles: RECEPTIONIST, LAB_STAFF, WARD_MANAGER, OPERATIONS_MANAGER.
    """
    staff = SupabaseHospitalClient.authenticate_staff(req.username, req.password)
    if not staff:
        raise HTTPException(status_code=401, detail="Invalid Staff ID or Password. Please verify your credentials.")
    
    token = _generate_staff_token({
        "sub": staff["staff_id"],
        "staff_id": staff["staff_id"],
        "role": staff["role"],
        "name": staff["name"],
        "department": staff.get("department", "")
    })
    return {
        "status": "success",
        "message": f"Welcome back, {staff['name']}.",
        "token": token,
        "user": staff
    }


@router.get("/auth/me", tags=["Staff Authentication"])
def get_current_staff(auth: Optional[Dict[str, Any]] = Depends(get_staff_context)):
    """Returns profile information for the authenticated staff member."""
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    staff = SupabaseHospitalClient.get_staff_by_id(auth["staff_id"])
    if not staff:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    return {"status": "success", "user": staff}


class PatientRegisterRequest(BaseModel):
    patient_id: Optional[str] = None
    full_name: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    doctor_name: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    symptoms: Optional[str] = None
    insurance_covered: Optional[bool] = False
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None


@router.post("/patients", tags=["Patient Management"])
def register_patient_record(req: PatientRegisterRequest):
    """Registers a new patient permanently in Supabase & SQLite."""
    try:
        data = req.model_dump()
        if not data.get("full_name") and data.get("name"):
            data["full_name"] = data["name"]
        elif not data.get("name") and data.get("full_name"):
            data["name"] = data["full_name"]
            
        import disease_prediction.api.database as db
        sqlite_res = db.register_patient_appointment(data)
        
        # Pass the unified patient_id to Supabase so both databases have identical ID and credentials
        if sqlite_res.get("patient_id"):
            data["patient_id"] = sqlite_res["patient_id"]
            
        try:
            patient = SupabaseHospitalClient.register_patient(data)
        except Exception as supa_err:
            logger.warning(f"Supabase registration error: {supa_err}")
            patient = dict(data)
        
        # Ensure identical PIN across both
        active_pin = sqlite_res.get("pin") or sqlite_res.get("access_pin") or f"PIN-{data.get('patient_id', '1001').split('-')[-1]}"
        patient["pin"] = active_pin
        patient["access_pin"] = active_pin
        patient["patient_id"] = data.get("patient_id", sqlite_res.get("patient_id"))
            
        if sqlite_res.get("appointment_id"):
            patient["appointment_id"] = sqlite_res["appointment_id"]
            patient["appointment"] = sqlite_res
            
        return patient
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register patient: {str(e)}")



@router.get("/patients", tags=["Patient Management"])
def list_patients(q: Optional[str] = None, query: Optional[str] = None, limit: int = 50):
    """Lists & searches persistent patients from Supabase and registered directory."""
    try:
        search_query = q or query
        import disease_prediction.api.database as db
        sqlite_patients = []
        try:
            sqlite_patients = db.get_all_patients_public()
        except Exception:
            pass
            
        supa_patients = []
        try:
            supa_patients = SupabaseHospitalClient.list_patients(query=search_query, limit=limit)
        except Exception:
            pass
            
        seen = set()
        merged = []
        
        # Priority to exact match if query provided
        for p in sqlite_patients:
            pid = p.get("patient_id") or p.get("id")
            pname = p.get("name") or p.get("full_name") or ""
            pphone = p.get("phone") or p.get("contact") or ""
            if search_query:
                sq = search_query.lower()
                if sq not in (pid or "").lower() and sq not in pname.lower() and sq not in pphone.lower():
                    continue
            if pid and pid not in seen:
                seen.add(pid)
                merged.append({
                    "patient_id": pid,
                    "full_name": pname,
                    "name": pname,
                    "age": p.get("age"),
                    "gender": p.get("gender"),
                    "phone": pphone,
                    "email": p.get("email"),
                    "status": "Registered"
                })
                
        for sp in supa_patients:
            spid = sp.get("patient_id")
            if spid and spid not in seen:
                seen.add(spid)
                merged.append(sp)
                
        return merged[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list patients: {str(e)}")


class PatientAdmissionRequest(BaseModel):
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    has_insurance: Optional[bool] = False
    insurance_covered: Optional[bool] = False
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    tpa_number: Optional[str] = None
    coverage_limit_inr: Optional[float] = 0.0
    claim_status: Optional[str] = "Pending Pre-Auth"
    preferred_bed_type: Optional[str] = "General"  # General, AC, Premium
    preferred_bed_tier: Optional[str] = "General"
    assigned_bed_id: Optional[str] = None
    assigned_ward: Optional[str] = None
    ward_name: Optional[str] = None
    admitting_department: Optional[str] = None
    admitting_doctor: Optional[str] = None
    attending_doctor: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    clinical_notes: Optional[str] = None


@router.get("/beds/inventory")
def get_supabase_bed_inventory(
    bed_type: Optional[str] = Query(None, description="Filter by tier: General, AC, Premium"),
    ward_name: Optional[str] = Query(None, description="Filter by ward"),
    status: Optional[str] = Query(None, description="Filter by status: Available, Occupied, Maintenance")
):
    """Returns live bed inventory from Supabase categorized by General, AC, and Premium tiers."""
    try:
        beds = SupabaseHospitalClient.get_bed_inventory(bed_type=bed_type, ward_name=ward_name, status=status)
        return beds
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bed inventory: {str(e)}")


@router.get("/beds/tiers")
def get_supabase_bed_tiers():
    """Returns 3-tier occupancy and pricing summary for General, AC, and Premium beds from Supabase."""
    try:
        return SupabaseHospitalClient.get_bed_tiers_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bed tiers summary: {str(e)}")


class BedStatusUpdateRequest(BaseModel):
    status: str  # Available, Occupied, Needs Cleaning, Maintenance
    current_patient_id: Optional[str] = None


@router.post("/beds/{bed_id}/status")
def update_bed_status_endpoint(bed_id: str, req: BedStatusUpdateRequest):
    """Updates bed status directly in Supabase (e.g., Available, Occupied, Needs Cleaning)."""
    try:
        updated = SupabaseHospitalClient.update_bed_status(bed_id, req.status, req.current_patient_id)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Bed ID '{bed_id}' not found.")
        return {"status": "success", "message": f"Bed {bed_id} status updated to '{req.status}' in Supabase.", "bed": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bed status: {str(e)}")


@router.post("/admissions")

def create_patient_admission_entry(req: PatientAdmissionRequest):
    """
    Admits a patient in Supabase with insurance information, bed tier preference, and allocates a bed.
    Enforces Bed Quota validation.
    """
    try:
        data = req.model_dump()
        if not data.get("full_name") and data.get("patient_name"):
            data["full_name"] = data["patient_name"]
        elif not data.get("patient_name") and data.get("full_name"):
            data["patient_name"] = data["full_name"]
        if not data.get("preferred_bed_type") and data.get("preferred_bed_tier"):
            data["preferred_bed_type"] = data["preferred_bed_tier"]
        elif not data.get("preferred_bed_tier") and data.get("preferred_bed_type"):
            data["preferred_bed_tier"] = data["preferred_bed_type"]
        if not data.get("assigned_ward") and data.get("ward_name"):
            data["assigned_ward"] = data["ward_name"]
        elif not data.get("ward_name") and data.get("assigned_ward"):
            data["ward_name"] = data["assigned_ward"]
        if not data.get("admitting_doctor") and data.get("attending_doctor"):
            data["admitting_doctor"] = data["attending_doctor"]
        elif not data.get("attending_doctor") and data.get("admitting_doctor"):
            data["attending_doctor"] = data["admitting_doctor"]

        admission = SupabaseHospitalClient.create_admission(data)
        return admission
    except ValueError as ve:
        err_msg = str(ve)
        if "BED_QUOTA_FULL" in err_msg:
            raise HTTPException(status_code=400, detail="🔴 BED QUOTA FULL: No available beds in the selected category.")
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient admission: {str(e)}")


@router.get("/admissions")
def list_supabase_admissions(
    status: Optional[str] = Query(None, description="Filter by status: Active, Discharged, Transferred"),
    limit: int = 50
):
    """Lists recent patient admissions and insurance records from Supabase."""
    try:
        admissions = SupabaseHospitalClient.list_admissions(status=status, limit=limit)
        return admissions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list admissions: {str(e)}")


@router.post("/admissions/{admission_id}/discharge")
def discharge_admitted_patient(admission_id: str):
    """Discharges a patient and marks their assigned bed as Available in Supabase."""
    try:
        res = SupabaseHospitalClient.discharge_patient(admission_id)
        if not res:
            raise HTTPException(status_code=404, detail=f"Active admission {admission_id} not found.")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discharge patient: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discharge patient: {str(e)}")


# ---------------------------------------------------------
# LABORATORY ORDERS & RESULT UPDATES
# ---------------------------------------------------------
@router.get("/lab/orders")
def get_supabase_lab_orders(
    status: Optional[str] = Query(None, description="Filter: Pending, Completed, Delayed"),
    limit: int = 50
):
    """Lists lab orders from Supabase."""
    try:
        orders = SupabaseHospitalClient.list_lab_orders(status=status, limit=limit)
        return {"total": len(orders), "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch lab orders: {str(e)}")


class LabResultUpdateRequest(BaseModel):
    order_id: str
    is_delayed: Optional[bool] = None


@router.post("/lab/orders/{order_id}/result")
def complete_lab_order(order_id: str, req: Optional[LabResultUpdateRequest] = None):
    """Marks a laboratory test order as Completed in Supabase and recalculates TAT."""
    try:
        is_delayed = req.is_delayed if req else None
        res = SupabaseHospitalClient.update_lab_result(order_id, is_delayed=is_delayed)
        if not res:
            raise HTTPException(status_code=404, detail=f"Lab order {order_id} not found.")
        return {
            "status": "success",
            "message": f"Lab order {order_id} marked as Completed. Turnaround time updated.",
            "order": res
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update lab order: {str(e)}")


class BillGenerateRequest(BaseModel):
    patient_id: str
    patient_name: str
    admission_id: Optional[str] = None
    bed_type: str = "General"  # General (₹800), AC (₹1800), Premium (₹4500)
    bed_id: Optional[str] = "BED-GEN-101"
    admitted_date: Optional[str] = None
    discharge_date: Optional[str] = None
    days_stayed: int = 3
    doctor_name: Optional[str] = "Dr. Ramesh Gupta"
    doctor_visits_count: int = 3
    doctor_fee_per_visit: float = 800.0
    lab_tests_fee: float = 1200.0
    nursing_fee_per_day: float = 500.0
    medicines_fee: float = 1500.0
    linen_fee_per_day: float = 0.0   # bedsheets & linen
    food_fee_per_day: float = 0.0    # meals
    extra_charges: Optional[List[Dict[str, Any]]] = []  # [{label, amount}]
    is_insured: bool = False
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_percentage: float = 80.0


# Ward daily amenity rates by tier
WARD_AMENITY_RATES = {
    "General":  {"linen": 80.0,  "food": 180.0, "housekeeping": 60.0},
    "AC":       {"linen": 150.0, "food": 280.0, "housekeeping": 100.0},
    "Premium":  {"linen": 300.0, "food": 450.0, "housekeeping": 200.0},
    "ICU":      {"linen": 300.0, "food": 0.0,   "housekeeping": 200.0},
}


@router.post("/billing/calculate")
def calculate_patient_inpatient_bill(req: BillGenerateRequest):
    """
    Calculates detailed itemized billing invoice for an inpatient.
    Includes bed tier, stay duration, doctor visits, ward amenities (linen/food), custom extras, and insurance deductions.
    """
    tier_rates = {"General": 800.0, "AC": 1800.0, "Premium": 4500.0}
    amenity = WARD_AMENITY_RATES.get(req.bed_type, WARD_AMENITY_RATES["General"])

    daily_bed_rate = tier_rates.get(req.bed_type, 800.0)
    days = max(1, req.days_stayed)

    total_bed_charges = daily_bed_rate * days
    total_doctor_charges = req.doctor_fee_per_visit * max(1, req.doctor_visits_count)
    total_nursing_charges = req.nursing_fee_per_day * days
    total_lab_charges = req.lab_tests_fee
    total_pharmacy_charges = req.medicines_fee

    # Ward amenities
    linen_rate = req.linen_fee_per_day if req.linen_fee_per_day > 0 else amenity["linen"]
    food_rate = req.food_fee_per_day if req.food_fee_per_day > 0 else amenity["food"]
    housekeeping_rate = amenity["housekeeping"]
    total_linen_charges = round(linen_rate * days, 2)
    total_food_charges = round(food_rate * days, 2)
    total_housekeeping_charges = round(housekeeping_rate * days, 2)

    # Extra custom charges
    extras = req.extra_charges or []
    total_extras = round(sum(float(e.get("amount", 0)) for e in extras), 2)

    gross_subtotal = round(
        total_bed_charges + total_doctor_charges + total_nursing_charges +
        total_lab_charges + total_pharmacy_charges +
        total_linen_charges + total_food_charges + total_housekeeping_charges +
        total_extras, 2
    )
    tax_gst = round(gross_subtotal * 0.05, 2)
    gross_total = round(gross_subtotal + tax_gst, 2)

    if req.is_insured:
        insurance_deduction = round(gross_total * (req.coverage_percentage / 100.0), 2)
        net_payable = max(0.0, round(gross_total - insurance_deduction, 2))
    else:
        insurance_deduction = 0.0
        net_payable = gross_total

    bill_id = f"INV-2026-{req.patient_id.replace('PAT-', '') if req.patient_id else '8891'}"

    bill_data = {
        "status": "success",
        "bill_id": bill_id,
        "patient_id": req.patient_id,
        "patient_name": req.patient_name,
        "admission_id": req.admission_id,
        "bed_id": req.bed_id,
        "bed_type": req.bed_type,
        "days_stayed": days,
        "daily_bed_rate": daily_bed_rate,
        "total_bed_charges": total_bed_charges,
        "total_doctor_charges": total_doctor_charges,
        "total_nursing_charges": total_nursing_charges,
        "total_lab_charges": total_lab_charges,
        "total_pharmacy_charges": total_pharmacy_charges,
        "total_linen_charges": total_linen_charges,
        "total_food_charges": total_food_charges,
        "total_housekeeping_charges": total_housekeeping_charges,
        "extra_charges": extras,
        "total_extras": total_extras,
        "gross_subtotal": gross_subtotal,
        "tax_gst": tax_gst,
        "gross_total": gross_total,
        "is_insured": req.is_insured,
        "insurance_provider": req.insurance_provider,
        "policy_number": req.policy_number,
        "insurance_deduction": insurance_deduction,
        "net_payable": net_payable
    }

    # Save invoice to Supabase
    try:
        SupabaseHospitalClient.save_billing_invoice(bill_data)
    except Exception as e:
        print(f"[BILLING-WARN] Failed to auto-persist invoice to Supabase: {e}")

    return bill_data


@router.post("/billing/save")
def save_inpatient_billing_invoice(invoice_data: Dict[str, Any]):
    """Persists a calculated inpatient invoice directly in Supabase."""
    try:
        res = SupabaseHospitalClient.save_billing_invoice(invoice_data)
        return {"status": "success", "message": "Invoice saved to Supabase.", "invoice": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save billing invoice: {str(e)}")


@router.get("/billing/invoices")
def list_inpatient_billing_invoices(patient_id: Optional[str] = Query(None), limit: int = 50):
    """Lists persistent inpatient billing invoices from Supabase."""
    try:
        invoices = SupabaseHospitalClient.list_billing_invoices(patient_id=patient_id, limit=limit)
        return {"total": len(invoices), "invoices": invoices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list billing invoices: {str(e)}")


class MarkPaidRequest(BaseModel):
    admission_id: str
    patient_id: str
    bill_id: Optional[str] = None
    net_payable: Optional[float] = 0.0


@router.post("/billing/mark-paid")
def mark_bill_as_paid(req: MarkPaidRequest):
    """
    Marks a patient bill as PAID.
    1. Discharges the patient (frees the bed) if still Active.
    2. Updates invoice status to 'Paid' in Supabase billing_invoices.
    3. Returns updated state for frontend to refresh.
    """
    try:
        # Step 1: Discharge the patient (frees bed)
        discharge_result = None
        try:
            discharge_result = SupabaseHospitalClient.discharge_patient(req.admission_id)
        except Exception as de:
            print(f"[BILLING-MARK-PAID] Discharge attempt: {de} (may already be discharged)")

        # Step 2: Update billing invoice to Paid
        sb = SupabaseHospitalClient.get_connection()
        sc = sb.cursor()
        if req.bill_id:
            sc.execute(
                "UPDATE billing_invoices SET status = 'Paid' WHERE invoice_id = %s",
                (req.bill_id,)
            )
        else:
            sc.execute(
                "UPDATE billing_invoices SET status = 'Paid' WHERE patient_id = %s AND status != 'Paid'",
                (req.patient_id,)
            )
        sb.commit()
        sb.close()

        return {
            "status": "success",
            "message": f"Bill for patient {req.patient_id} marked as PAID. Bed freed.",
            "discharge": discharge_result,
            "bill_id": req.bill_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark bill as paid: {str(e)}")


@router.get("/billing/amenity-rates")
def get_ward_amenity_rates():
    """Returns daily amenity charge rates per bed tier for ward monetization display."""
    return WARD_AMENITY_RATES


@router.get("/patient-location")
def get_patient_location(q: str = Query(..., description="Patient name or Patient ID")):
    """
    Tracks exact patient location across the hospital.
    Returns: Active (ward + bed), Outpatient (appointment), or Discharged (with bill info).
    """
    try:
        q_lower = q.strip().lower()
        result = {"query": q, "found": False}

        # 1. Search active/discharged admissions in Supabase
        try:
            sb = SupabaseHospitalClient.get_connection()
            sc = sb.cursor()
            sc.execute("""
                SELECT pa.admission_id, pa.patient_id, pa.full_name, pa.age, pa.gender,
                       pa.assigned_bed_id, pa.assigned_ward, pa.admitting_doctor,
                       pa.admitting_department, pa.admission_date, pa.discharge_date,
                       pa.status, pa.has_insurance, pa.insurance_provider,
                       pa.preferred_bed_type,
                       hb.ward_name, hb.bed_type, hb.daily_rate_inr
                FROM patient_admissions pa
                LEFT JOIN hospital_beds hb ON pa.assigned_bed_id = hb.bed_id
                WHERE LOWER(pa.full_name) LIKE %s OR pa.patient_id = %s
                ORDER BY pa.admission_date DESC
                LIMIT 5
            """, (f"%{q_lower}%", q.strip()))
            admissions = sc.fetchall()
            sb.close()

            if admissions:
                adm = admissions[0]
                (adm_id, pat_id, full_name, age, gender,
                 bed_id, ward, doctor, dept, adm_date, disc_date,
                 status, has_ins, ins_provider, bed_type,
                 ward_name, hb_bed_type, daily_rate) = adm

                # Days stayed
                from datetime import datetime as dt
                try:
                    adm_dt = dt.fromisoformat(str(adm_date).replace('Z','').split('+')[0]) if adm_date else dt.now()
                    end_dt = dt.fromisoformat(str(disc_date).replace('Z','').split('+')[0]) if disc_date else dt.now()
                    days = max(1, (end_dt - adm_dt).days or 1)
                except Exception:
                    days = 1

                # Fetch bill info if discharged
                bill_info = None
                try:
                    sb2 = SupabaseHospitalClient.get_connection()
                    sc2 = sb2.cursor()
                    sc2.execute(
                        "SELECT invoice_id, net_payable, status FROM billing_invoices WHERE patient_id = %s ORDER BY created_at DESC LIMIT 1",
                        (pat_id,)
                    )
                    bill_row = sc2.fetchone()
                    sb2.close()
                    if bill_row:
                        bill_info = {"bill_id": bill_row[0], "invoice_id": bill_row[0], "net_payable": float(bill_row[1] or 0), "bill_status": bill_row[2]}
                except Exception:
                    pass

                result = {
                    "found": True,
                    "source": "inpatient",
                    "admission_id": adm_id,
                    "patient_id": pat_id,
                    "full_name": full_name,
                    "age": age,
                    "gender": gender,
                    "status": status,
                    "bed_id": bed_id,
                    "ward": ward_name or ward or "—",
                    "bed_type": hb_bed_type or bed_type or "General",
                    "daily_rate": float(daily_rate or 0),
                    "attending_doctor": doctor or "—",
                    "department": dept or "—",
                    "admission_date": str(adm_date)[:10] if adm_date else None,
                    "discharge_date": str(disc_date)[:10] if disc_date else None,
                    "days_stayed": days,
                    "has_insurance": bool(has_ins),
                    "insurance_provider": ins_provider or "—",
                    "bill": bill_info
                }
                return result
        except Exception as se:
            print(f"[PATIENT-LOCATION] Supabase search error: {se}")

        # 2. Fallback: Search outpatient appointments in SQLite
        import disease_prediction.api.database as db
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.appointment_id, a.patient_id, a.full_name, a.age, a.gender,
                   a.department, a.doctor_name, a.appointment_date, a.time_slot,
                   a.status, p.contact, p.email
            FROM patient_appointments a
            LEFT JOIN patients p ON a.patient_id = p.patient_id
            WHERE LOWER(a.full_name) LIKE ? OR a.patient_id = ?
            ORDER BY a.appointment_date DESC
            LIMIT 3
        """, (f"%{q_lower}%", q.strip()))
        appts = cur.fetchall()

        if appts:
            a = appts[0]
            conn.close()
            result = {
                "found": True,
                "source": "outpatient",
                "appointment_id": a["appointment_id"],
                "patient_id": a["patient_id"],
                "full_name": a["full_name"],
                "age": a["age"],
                "gender": a["gender"],
                "status": "Outpatient",
                "department": a["department"],
                "attending_doctor": a["doctor_name"],
                "appointment_date": a["appointment_date"],
                "time_slot": a["time_slot"],
                "appointment_status": a["status"],
                "contact": a["contact"],
                "email": a["email"],
            }
            return result

        # 3. Fallback: Search primary patients directory in SQLite
        cur.execute("""
            SELECT patient_id, name, age, gender, contact, email, created_at
            FROM patients
            WHERE LOWER(name) LIKE ? OR patient_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (f"%{q_lower}%", q.strip()))
        pat = cur.fetchone()

        if pat:
            # Check for lab reports
            cur.execute("SELECT COUNT(*) as report_count FROM lab_reports WHERE patient_id = ?", (pat["patient_id"],))
            rep_cnt = cur.fetchone()["report_count"]
            conn.close()

            result = {
                "found": True,
                "source": "registered",
                "patient_id": pat["patient_id"],
                "full_name": pat["name"],
                "age": pat["age"],
                "gender": pat["gender"],
                "status": "Registered",
                "contact": pat["contact"],
                "email": pat["email"],
                "registered_on": str(pat["created_at"])[:10] if pat["created_at"] else "Recorded",
                "lab_reports_count": rep_cnt,
            }
            return result

        conn.close()
        result["message"] = f"No patient found matching '{q}'"
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Patient location search failed: {str(e)}")





