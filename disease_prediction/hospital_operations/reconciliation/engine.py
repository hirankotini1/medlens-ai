"""
Conflict Detection & Reconciliation Engine
"""
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from disease_prediction.hospital_operations.models import (
    NormalizedHISRecord,
    NormalizedLabRecord,
    NormalizedBedRecord,
    ConflictRecord
)
from disease_prediction.hospital_operations.normalization.standardizer import (
    CANONICAL_WARDS,
    WARD_CAPACITIES
)
from disease_prediction.hospital_operations.reconciliation.rules import (
    RECONCILIATION_RULES,
    get_rule_by_id
)


class HospitalReconciliationEngine:
    """
    Detects all operational discrepancies across HIS, LAB, and BED data sources,
    applies deterministic rules, and produces reconciled values with explanations.
    """

    def __init__(
        self,
        his_records: List[NormalizedHISRecord],
        lab_records: List[NormalizedLabRecord],
        bed_records: List[NormalizedBedRecord]
    ):
        self.his_records = his_records
        self.lab_records = lab_records
        self.bed_records = bed_records

    def execute_reconciliation(self) -> Dict[str, Any]:
        """
        Runs complete conflict detection and reconciliation pass.
        Returns list of ConflictRecord objects, summary counts, and reconciled data structures.
        """
        conflicts: List[ConflictRecord] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---------------------------------------------------------
        # 1. Conflict Category: Duplicate HIS Records
        # ---------------------------------------------------------
        for r in self.his_records:
            if r.is_duplicate:
                rule = get_rule_by_id("RULE-REC-02")
                conflicts.append(ConflictRecord(
                    conflict_id=f"CONF-DUP-{r.canonical_patient_id}-{r.row_index}",
                    category="DUPLICATE_HIS_RECORD",
                    source_a="HIS Admissions (Row " + str(r.duplicate_of) + ")",
                    source_b="HIS Admissions (Row " + str(r.row_index) + ")",
                    record_ref=f"Patient: {r.canonical_patient_id}",
                    source_a_value=f"Adm: {r.admission_datetime} | Ward: {r.canonical_ward}",
                    source_b_value=f"Adm: {r.admission_datetime} | Ward: {r.canonical_ward}",
                    difference_summary=f"Exact duplicate admission entry detected for patient {r.canonical_patient_id} (Row {r.row_index} vs Row {r.duplicate_of})",
                    applied_rule_id=rule.rule_id,
                    applied_rule_name=rule.rule_name,
                    resolution_status="Resolved",
                    reconciled_value=f"Primary admission retained (Row {r.duplicate_of})",
                    explanation_reason="Retained original admission entry for census and LOS calculations. Duplicate row flagged to prevent double-counting active beds.",
                    severity="Medium",
                    timestamp=now_str
                ))

        # ---------------------------------------------------------
        # 2. Conflict Category: Missing Available Value in Bed Sheet
        # ---------------------------------------------------------
        for r in self.bed_records:
            if r.was_available_imputed:
                rule = get_rule_by_id("RULE-REC-05")
                conflicts.append(ConflictRecord(
                    conflict_id=f"CONF-BED-AVAIL-{r.canonical_date}-{r.row_index}",
                    category="MISSING_FIELD",
                    source_a="Bed Occupancy Sheet (Available Field)",
                    source_b="Calculated (Total - Occupied)",
                    record_ref=f"Date: {r.canonical_date} | Ward: {r.canonical_ward}",
                    source_a_value=None,
                    source_b_value=r.available,
                    difference_summary=f"Available bed count was left blank in the manual nursing log for {r.canonical_ward} on {r.canonical_date}",
                    applied_rule_id=rule.rule_id,
                    applied_rule_name=rule.rule_name,
                    resolution_status="Resolved",
                    reconciled_value=r.available,
                    explanation_reason=f"Deterministically computed Available beds as {r.total_beds} Total - {r.occupied} Occupied = {r.available} Available.",
                    severity="Low",
                    timestamp=now_str
                ))

        # ---------------------------------------------------------
        # 3. Conflict Category: Outpatient Diagnostic Orders (Unmatched in HIS)
        # ---------------------------------------------------------
        outpatient_orders = [lr for lr in self.lab_records if lr.is_outpatient]
        seen_outpatient_pids = set()
        for lr in outpatient_orders:
            if lr.canonical_patient_id not in seen_outpatient_pids:
                seen_outpatient_pids.add(lr.canonical_patient_id)
                rule = get_rule_by_id("RULE-REC-01")
                conflicts.append(ConflictRecord(
                    conflict_id=f"CONF-OUTPATIENT-{lr.canonical_patient_id}",
                    category="OUTPATIENT_UNMATCHED",
                    source_a="Lab Order-to-Result (7xxx ID Series)",
                    source_b="HIS Inpatient Ledger",
                    record_ref=f"Patient: {lr.canonical_patient_id} ({lr.department})",
                    source_a_value=f"Order {lr.order_id}: {lr.test_name} ({lr.canonical_priority})",
                    source_b_value="No Inpatient Admission Record Found",
                    difference_summary=f"Lab order for patient {lr.canonical_patient_id} does not have a corresponding inpatient admission in HIS.",
                    applied_rule_id=rule.rule_id,
                    applied_rule_name=rule.rule_name,
                    resolution_status="Resolved",
                    reconciled_value="Categorized as Outpatient Diagnostic Service",
                    explanation_reason="Patient was registered for outpatient or emergency walk-in lab diagnostic testing without an inpatient bed allocation. Preserved in laboratory workload analytics.",
                    severity="Info",
                    timestamp=now_str
                ))

        # ---------------------------------------------------------
        # 4. Conflict Category: Missing Bed Sheet Days in July
        # ---------------------------------------------------------
        bed_dates_present = set(r.canonical_date for r in self.bed_records)
        all_july_dates = [f"2026-07-{day:02d}" for day in range(1, 31)]  # 1st to 30th July
        missing_bed_dates = sorted(list(set(all_july_dates) - bed_dates_present))

        for m_date in missing_bed_dates:
            rule = get_rule_by_id("RULE-REC-04")
            conflicts.append(ConflictRecord(
                conflict_id=f"CONF-MISSING-BED-DAY-{m_date}",
                category="MISSING_BED_SHEET_DAY",
                source_a="Manual Bed Occupancy Sheet",
                source_b="HIS Admissions & Discharges",
                record_ref=f"Date: {m_date} (Hospital-wide)",
                source_a_value="No Sheet Submitted (Missing)",
                source_b_value="Active HIS Admissions Available",
                difference_summary=f"Manual nursing bed sheet was not logged or submitted for date {m_date}.",
                applied_rule_id=rule.rule_id,
                applied_rule_name=rule.rule_name,
                resolution_status="Resolved",
                reconciled_value="Bed occupancy calculated from HIS timestamped active patient records",
                explanation_reason="Imputed ward bed occupancy counts using active HIS patient census. Tagged as IMPUTED_FROM_HIS to ensure transparency.",
                severity="High",
                timestamp=now_str
            ))

        # ---------------------------------------------------------
        # 5. Conflict Category: Bed Sheet Occupancy vs HIS Census Discrepancies
        # ---------------------------------------------------------
        # Build daily HIS occupancy map by (date_str, canonical_ward)
        # HIS active patient count on date D: adm <= D 23:59:59 and (dis is null or dis >= D 00:00:00)
        # Exclude duplicate records
        unique_his = [r for r in self.his_records if not r.is_duplicate]

        for bed_rec in self.bed_records:
            b_date = bed_rec.canonical_date
            b_ward = bed_rec.canonical_ward
            b_occ = bed_rec.occupied
            b_rem = bed_rec.remarks or ""

            # Calculate HIS active patients in that ward on that date
            day_start = f"{b_date} 00:00:00"
            day_end = f"{b_date} 23:59:59"

            his_active_in_ward = [
                h for h in unique_his
                if h.canonical_ward == b_ward
                and h.admission_datetime <= day_end
                and (h.discharge_datetime is None or h.discharge_datetime >= day_start)
            ]
            his_occ = len(his_active_in_ward)

            if his_occ != b_occ:
                rule = get_rule_by_id("RULE-REC-03")
                diff = b_occ - his_occ
                diff_sign = f"+{diff}" if diff > 0 else f"{diff}"

                # Determine reconciled value and reason based on remarks
                if bed_rec.has_daycare:
                    reconciled_val = f"Physical: {b_occ} beds (includes {bed_rec.daycare_count} day-care) | Inpatient Census: {b_occ - bed_rec.daycare_count}"
                    reason = f"Bed sheet notes '{b_rem}'. The difference of {diff_sign} reflects day-care patients occupying beds during the shift who are not logged as overnight inpatients."
                    status = "Resolved"
                    severity = "Medium"
                elif bed_rec.pending_discharge_count > 0:
                    reconciled_val = f"Physical: {b_occ} beds | Administrative: {his_occ} patients"
                    reason = f"Bed sheet notes '{b_rem}'. Patients completed medical discharge in HIS but remained physically in bed awaiting final paperwork clearance."
                    status = "Resolved"
                    severity = "Medium"
                elif bed_rec.is_system_downtime_approx:
                    reconciled_val = f"Verified HIS: {his_occ} active inpatients"
                    reason = f"Bed sheet notes '{b_rem}'. During IT downtime, manual counts were approximate. The timestamped HIS digital registry is prioritized as the verified ground truth."
                    status = "Resolved"
                    severity = "High"
                else:
                    reconciled_val = f"Bed Sheet: {b_occ} | HIS Census: {his_occ}"
                    reason = f"Shift count discrepancy of {diff_sign} patients between manual nursing log and HIS database. Potential intraday transfer or discharge logging lag."
                    status = "Needs_Review" if abs(diff) > 2 else "Resolved"
                    severity = "High" if abs(diff) > 2 else "Low"

                conflicts.append(ConflictRecord(
                    conflict_id=f"CONF-OCC-{b_date}-{bed_rec.row_index}",
                    category="BED_VS_HIS_OCCUPANCY",
                    source_a=f"Manual Bed Sheet ({b_occ} Beds)",
                    source_b=f"HIS Active Census ({his_occ} Patients)",
                    record_ref=f"Date: {b_date} | Ward: {b_ward}",
                    source_a_value=b_occ,
                    source_b_value=his_occ,
                    difference_summary=f"Manual Bed Sheet reports {b_occ} occupied beds while HIS records {his_occ} active admitted patients (Difference: {diff_sign}).",
                    applied_rule_id=rule.rule_id,
                    applied_rule_name=rule.rule_name,
                    resolution_status=status,
                    reconciled_value=reconciled_val,
                    explanation_reason=reason,
                    severity=severity,
                    timestamp=now_str
                ))

        # Sort conflicts by severity then date
        sev_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
        conflicts.sort(key=lambda c: (sev_order.get(c.severity, 5), c.record_ref))

        resolved_count = sum(1 for c in conflicts if c.resolution_status == "Resolved")
        needs_review_count = sum(1 for c in conflicts if c.resolution_status == "Needs_Review")

        return {
            "total_conflicts": len(conflicts),
            "resolved_count": resolved_count,
            "needs_review_count": needs_review_count,
            "conflicts": conflicts
        }
