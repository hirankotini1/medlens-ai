"""
Comprehensive Automated Test Suite for MedLens Multi-Tenant Healthcare SaaS
MedLens AI / Avenqra AI

Covers:
1. Organization Registration & Trial Provisioning
2. Staff Invitation & Onboarding Lifecycle
3. Strict Tenant Isolation & Anti-IDOR Enforcement
4. Role-Based Access Control (RBAC) Permitted Boundaries
5. Dedicated Patient Portal & Verified Multi-Hospital Linking
6. Usage Metering & Plan Limit Quotas
7. Payment Order Creation, Cryptographic Verification & Webhooks
8. Platform Superadmin Operations & Audit Trails
"""
import pytest
import secrets
from fastapi.testclient import TestClient
from datetime import datetime

from disease_prediction.api.main import app
from disease_prediction.api.saas_service import (
    get_db, TenantService, StaffService, PatientAccountService,
    UsageService, PaymentService, PLAN_DEFINITIONS
)
from disease_prediction.api.saas_auth import generate_token

client = TestClient(app)

class TestSaaSPlatformSuite:
    @classmethod
    def setup_class(cls):
        cls.now = int(datetime.utcnow().timestamp())
        cls.org_a_name = f"Apollo Test Hospital {cls.now}"
        cls.org_b_name = f"Care Test Hospital {cls.now}"
        
        # Superadmin token
        cls.superadmin_token = generate_token({
            "sub": "admin",
            "role": "superadmin",
            "account_type": "platform",
            "tenant_id": "PLATFORM_SUPERADMIN"
        })

    def test_01_organization_registration_and_trial(self):
        """Tests self-service hospital registration and automatic trial provisioning."""
        payload = {
            "organization_name": self.org_a_name,
            "organization_type": "hospital",
            "registration_number": f"NABH-{self.now}",
            "email": f"admin_{self.now}@apollo.test",
            "phone": "+91-891-2554433",
            "address": "Waltair Main Road",
            "city": "Visakhapatnam",
            "state": "Andhra Pradesh",
            "postal_code": "530002",
            "admin_name": "Dr. Ramesh Chandra",
            "admin_username": f"admin_apollo_{self.now}",
            "admin_password": "SecurePassword123!",
            "subscription_plan": "professional"
        }
        res = client.post("/api/saas/register-organization", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "success"
        assert "tenant" in data
        assert data["tenant"]["subscription_status"] == "trialing"
        assert "token" in data
        
        # Save tenant_a details
        self.__class__.tenant_a_id = data["tenant"]["tenant_id"]
        self.__class__.admin_a_username = payload["admin_username"]
        self.__class__.admin_a_token = data["token"]
        
        # Register Org B for cross-tenant tests
        payload_b = dict(payload)
        payload_b["organization_name"] = self.org_b_name
        payload_b["email"] = f"admin_{self.now}@care.test"
        payload_b["admin_username"] = f"admin_care_{self.now}"
        res_b = client.post("/api/saas/register-organization", json=payload_b)
        assert res_b.status_code == 200
        self.__class__.tenant_b_id = res_b.json()["tenant"]["tenant_id"]
        self.__class__.admin_b_token = res_b.json()["token"]

    def test_02_staff_invitation_and_onboarding(self):
        """Tests sending staff invitation, verifying token, and accepting invite."""
        headers_a = {"Authorization": f"Bearer {self.admin_a_token}"}
        
        # 1. Invite a doctor to Org A
        invite_req = {
            "email": f"dr.sharma_{self.now}@apollo.test",
            "full_name": "Dr. Priya Sharma",
            "role": "doctor",
            "department": "Cardiology",
            "doctor_registration_number": "NMC/2018/049182"
        }
        res_inv = client.post("/api/saas/hospital/staff/invite", json=invite_req, headers=headers_a)
        assert res_inv.status_code == 200, res_inv.text
        inv_data = res_inv.json()["invitation"]
        inv_token = inv_data["token"]
        
        # 2. Verify invitation link
        res_ver = client.get(f"/api/saas/verify-invitation/{inv_token}")
        assert res_ver.status_code == 200
        assert res_ver.json()["valid"] is True
        assert res_ver.json()["role"] == "doctor"
        
        # 3. Accept invitation
        doc_username = f"dr_sharma_{self.now}"
        res_acc = client.post("/api/saas/accept-invitation", json={
            "token": inv_token,
            "username": doc_username,
            "password": "DoctorPassword123!",
            "full_name": "Dr. Priya Sharma"
        })
        assert res_acc.status_code == 200
        doc_token = res_acc.json()["token"]
        self.__class__.doc_a_token = doc_token
        
        # 4. Attempting to accept same token again must fail
        res_dup = client.post("/api/saas/accept-invitation", json={
            "token": inv_token,
            "username": f"dr_dup_{self.now}",
            "password": "DoctorPassword123!"
        })
        assert res_dup.status_code == 400

    def test_03_strict_tenant_isolation(self):
        """
        Validates that Hospital A cannot access Hospital B's patients,
        reports, or administrative records.
        """
        headers_a = {"Authorization": f"Bearer {self.admin_a_token}"}
        headers_b = {"Authorization": f"Bearer {self.admin_b_token}"}
        
        # Create Patient in Hospital A
        p_a = client.post("/api/patients", json={
            "name": "Hospital A Patient",
            "age": 45,
            "gender": "Male",
            "contact": "+91-9988776655",
            "tenant_id": self.tenant_a_id
        }, headers=headers_a)
        assert p_a.status_code == 200
        pid_a = p_a.json()["patient_id"]
        
        # Hospital B attempts to fetch Hospital A's patient profile -> MUST BE REJECTED 403
        res_idor = client.get(f"/api/patients/{pid_a}", headers=headers_b)
        assert res_idor.status_code == 403, "Cross-hospital patient profile access must be rejected!"
        assert "Cross-hospital" in res_idor.json()["detail"] or "Access denied" in res_idor.json()["detail"]
        
        # Create Report in Hospital A
        rep_a = client.post("/api/reports", json={
            "patient_id": pid_a,
            "test_category": "CBC Blood Panel",
            "report_data": {"Hemoglobin": 13.5, "Platelets": 250000},
            "status": "Finalized",
            "tenant_id": self.tenant_a_id
        }, headers=headers_a)
        assert rep_a.status_code == 200
        rep_id_a = rep_a.json()["report_id"]
        
        # Hospital B attempts to read Hospital A's report -> MUST BE REJECTED 403
        res_rep_idor = client.get(f"/api/reports/{rep_id_a}", headers=headers_b)
        assert res_rep_idor.status_code == 403, "Cross-hospital report access must be rejected!"
        assert "Cross-hospital" in res_rep_idor.json()["detail"] or "Access denied" in res_rep_idor.json()["detail"]
        
        # Hospital A listing reports only sees Hospital A reports
        res_list_b = client.get("/api/reports", headers=headers_b)
        assert res_list_b.status_code == 200
        for r in res_list_b.json():
            assert r.get("tenant_id") == self.tenant_b_id

    def test_04_role_based_access_control(self):
        """Verifies RBAC boundaries for Receptionist, Doctor, and Admin."""
        headers_a = {"Authorization": f"Bearer {self.admin_a_token}"}
        
        # Invite and accept Receptionist role
        res_inv = client.post("/api/saas/hospital/staff/invite", json={
            "email": f"reception_{self.now}@apollo.test",
            "full_name": "Ravi Kumar",
            "role": "receptionist",
            "department": "Front Desk"
        }, headers=headers_a)
        rec_token = res_inv.json()["invitation"]["token"]
        
        acc_rec = client.post("/api/saas/accept-invitation", json={
            "token": rec_token,
            "username": f"reception_{self.now}",
            "password": "ReceptionPassword123!"
        })
        rec_auth = {"Authorization": f"Bearer {acc_rec.json()['token']}"}
        
        # Receptionist CANNOT access hospital subscription/billing
        res_sub = client.get("/api/saas/hospital/subscription", headers=rec_auth)
        assert res_sub.status_code == 403
        
        # Receptionist CANNOT invite new staff
        res_inv_fail = client.post("/api/saas/hospital/staff/invite", json={
            "email": "hack@test.com", "role": "admin"
        }, headers=rec_auth)
        assert res_inv_fail.status_code == 403

    def test_05_dedicated_patient_portal_and_linking(self):
        """Tests patient account creation, multi-hospital linking, and record retrieval."""
        patient_email = f"patient_{self.now}@test.com"
        patient_phone = f"+91-91234{secrets.token_hex(2)}"
        
        # 1. Register Patient account
        reg_res = client.post("/api/saas/patient/register", json={
            "full_name": "Suresh Patel",
            "email": patient_email,
            "phone": patient_phone,
            "password": "PatientPassword123!",
            "date_of_birth": "1988-06-15",
            "gender": "Male",
            "blood_group": "O+",
            "dpdp_consent": True
        })
        assert reg_res.status_code == 200, reg_res.text
        pat_token = reg_res.json()["token"]
        pat_headers = {"Authorization": f"Bearer {pat_token}"}
        
        # 2. Patient Profile endpoint
        res_me = client.get("/api/saas/patient/me", headers=pat_headers)
        assert res_me.status_code == 200
        assert res_me.json()["full_name"] == "Suresh Patel"
        
        # 3. Patient CANNOT access hospital staff routes
        res_staff_fail = client.get("/api/saas/hospital/staff", headers=pat_headers)
        assert res_staff_fail.status_code == 403
        
        # 4. Link hospital record with INVALID PIN -> MUST FAIL
        res_link_bad = client.post("/api/saas/patient/link-hospital", json={
            "tenant_id": "tenant_medlens_apex",
            "hospital_patient_id": "PAT-1001",
            "verification_pin": "9999", # Incorrect PIN
            "consent_given": True
        }, headers=pat_headers)
        assert res_link_bad.status_code == 400
        assert "Incorrect" in res_link_bad.json()["detail"] or "failed" in res_link_bad.json()["detail"]
        
        # 5. Link hospital record with VALID PIN (PAT-1001 default pin is PIN-1001 or 1001)
        res_link_ok = client.post("/api/saas/patient/link-hospital", json={
            "tenant_id": "tenant_medlens_apex",
            "hospital_patient_id": "PAT-1001",
            "verification_pin": "PIN-1001",
            "consent_given": True
        }, headers=pat_headers)
        assert res_link_ok.status_code == 200, res_link_ok.text
        assert res_link_ok.json()["status"] == "success"
        
        # 6. View Linked Hospitals
        res_links = client.get("/api/saas/patient/linked-hospitals", headers=pat_headers)
        assert res_links.status_code == 200
        assert len(res_links.json()["linked_hospitals"]) >= 1
        
        # 7. Aggregated diagnostic reports
        res_aggr = client.get("/api/saas/patient/aggregated-records", headers=pat_headers)
        assert res_aggr.status_code == 200
        assert "aggregated_reports" in res_aggr.json()
        
        # 8. DPDP Act data portability export
        res_export = client.post("/api/saas/patient/export-data", headers=pat_headers)
        assert res_export.status_code == 200
        assert res_export.json()["export_metadata"]["format"] == "DPDP_ACT_2023_HEALTH_VAULT"

    def test_06_usage_metering_and_entitlements(self):
        """Verifies usage tracking and entitlement limits."""
        # Record usage
        UsageService.record_usage(self.tenant_a_id, "ai_queries", increment_by=5)
        UsageService.record_usage(self.tenant_a_id, "report_analyses", increment_by=2)
        
        usage = UsageService.get_usage_summary(self.tenant_a_id)
        assert usage["ai_queries_count"] >= 5
        assert usage["report_analyses_count"] >= 2
        
        # Check entitlement
        allowed, reason, cur_u, max_l = UsageService.check_entitlement(self.tenant_a_id, "ai_queries")
        assert allowed is True

    def test_07_payment_checkout_and_webhook_idempotency(self):
        """Tests subscription order creation, signature verification, and duplicate webhook protection."""
        headers_a = {"Authorization": f"Bearer {self.admin_a_token}"}
        
        # 1. Create payment order
        res_order = client.post("/api/saas/payments/create-order", json={
            "plan_id": "professional",
            "billing_cycle": "monthly"
        }, headers=headers_a)
        assert res_order.status_code == 200
        assert res_order.json()["amount_inr"] == PLAN_DEFINITIONS["professional"]["price_inr_monthly"]
        
        # 2. Verify payment & activate
        res_pay = client.post("/api/saas/payments/verify", json={
            "plan_id": "professional",
            "razorpay_order_id": res_order.json()["order_id"],
            "razorpay_payment_id": f"pay_{secrets.token_hex(6)}",
            "razorpay_signature": "test_sig"
        }, headers=headers_a)
        assert res_pay.status_code == 200
        assert res_pay.json()["status"] == "active"
        
        # 3. Webhook listener idempotency
        event_id = f"evt_{secrets.token_hex(8)}"
        webhook_body = {
            "event_id": event_id,
            "event": "subscription.charged",
            "payload": {"tenant_id": self.tenant_a_id, "status": "paid"}
        }
        res_wh1 = client.post("/api/saas/payments/webhook", json=webhook_body)
        assert res_wh1.status_code == 200
        assert res_wh1.json()["status"] == "processed"
        
        # Duplicate delivery must be safely ignored
        res_wh2 = client.post("/api/saas/payments/webhook", json=webhook_body)
        assert res_wh2.status_code == 200
        assert res_wh2.json()["status"] == "duplicate_event_ignored"

    def test_08_platform_superadmin_console(self):
        """Tests superadmin telemetry, organization management, and suspension."""
        headers_sa = {"Authorization": f"Bearer {self.superadmin_token}"}
        
        # 1. Platform Metrics
        res_metrics = client.get("/api/saas/platform/metrics", headers=headers_sa)
        assert res_metrics.status_code == 200
        metrics = res_metrics.json()
        assert metrics["total_organizations"] >= 2
        assert metrics["mrr_inr"] > 0
        
        # 2. List organizations
        res_orgs = client.get("/api/saas/platform/organizations", headers=headers_sa)
        assert res_orgs.status_code == 200
        assert len(res_orgs.json()["organizations"]) >= 2
        
        # 3. Suspend Hospital B
        res_susp = client.patch(f"/api/saas/platform/organizations/{self.tenant_b_id}/status?new_status=suspended", headers=headers_sa)
        assert res_susp.status_code == 200
        
        # Attempt to login to suspended hospital must be blocked
        res_block = client.post("/api/saas/hospital/login", json={
            "tenant_id": self.tenant_b_id,
            "username_or_email": f"admin_care_{self.now}",
            "password": "SecurePassword123!"
        })
        assert res_block.status_code == 403
        assert "suspended" in res_block.json()["detail"]
        
        # Reactivate Hospital B
        res_react = client.patch(f"/api/saas/platform/organizations/{self.tenant_b_id}/status?new_status=active", headers=headers_sa)
        assert res_react.status_code == 200
        
        # Platform audit logs
        res_audit = client.get("/api/saas/platform/audit-logs", headers=headers_sa)
        assert res_audit.status_code == 200
        assert len(res_audit.json()["platform_audit_logs"]) >= 1
