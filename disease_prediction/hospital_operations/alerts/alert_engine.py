"""
Operational Alert & Bottleneck Detection Engine
"""
from typing import List, Dict, Any
from datetime import datetime
from disease_prediction.hospital_operations.models import (
    OperationalAlert,
    BedCapacityMetrics,
    LabPerformanceMetrics,
    PatientFlowMetrics,
    DataQualityMetrics,
    ConflictRecord
)


class HospitalAlertEngine:
    """
    Generates actionable operational alerts across bed capacity,
    diagnostic laboratory bottlenecks, and data reconciliation flags.
    """

    @staticmethod
    def generate_alerts(
        bed_metrics: BedCapacityMetrics,
        lab_metrics: LabPerformanceMetrics,
        flow_metrics: PatientFlowMetrics,
        quality_metrics: DataQualityMetrics,
        conflicts: List[ConflictRecord]
    ) -> List[OperationalAlert]:
        alerts: List[OperationalAlert] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---------------------------------------------------------
        # 1. Capacity & Ward Utilization Alerts
        # ---------------------------------------------------------
        for ward in bed_metrics.ward_breakdown:
            w_name = ward["ward_name"]
            w_pct = ward["occupancy_percentage"]
            w_avail = ward["available_beds"]

            if w_pct >= bed_metrics.configured_critical_threshold:
                alerts.append(OperationalAlert(
                    alert_id=f"ALT-CAP-CRIT-{w_name.replace(' ', '_')}",
                    severity="Critical",
                    icon="emergency",
                    title=f"Critical Bed Surge in {w_name}",
                    message=f"{w_name} is operating at {w_pct}% occupancy with only {w_avail} bed(s) available.",
                    category="Capacity",
                    affected_entity=w_name,
                    recommended_action="Initiate step-down patient transfer protocol and review pending discharge clearance.",
                    timestamp=now_str
                ))
            elif w_pct >= bed_metrics.configured_warning_threshold:
                alerts.append(OperationalAlert(
                    alert_id=f"ALT-CAP-WARN-{w_name.replace(' ', '_')}",
                    severity="Warning",
                    icon="warning",
                    title=f"Elevated Occupancy in {w_name}",
                    message=f"{w_name} is at {w_pct}% capacity ({w_avail} beds available).",
                    category="Capacity",
                    affected_entity=w_name,
                    recommended_action="Alert nursing supervisor to coordinate upcoming elective admissions.",
                    timestamp=now_str
                ))

        # ---------------------------------------------------------
        # 2. Laboratory Turnaround & STAT Bottlenecks
        # ---------------------------------------------------------
        stat_perf = lab_metrics.priority_performance.get("STAT", {})
        stat_avg_hours = stat_perf.get("avg_turnaround_hours", 0.0)
        routine_avg_hours = lab_metrics.priority_performance.get("ROUTINE", {}).get("avg_turnaround_hours", 0.0)

        if stat_avg_hours > 4.0:
            alerts.append(OperationalAlert(
                alert_id="ALT-LAB-STAT-BOTTLENECK",
                severity="Critical",
                icon="speed",
                title="STAT Diagnostic Turnaround Bottleneck Detected",
                message=(
                    f"STAT emergency tests average {stat_avg_hours} hours turnaround (virtually identical to "
                    f"Routine tests at {routine_avg_hours} hours). No prioritization acceleration detected."
                ),
                category="Turnaround",
                affected_entity="Central Pathology Laboratory",
                recommended_action="Activate dedicated STAT rapid-processing bench and investigate phlebotomy collection delays.",
                timestamp=now_str
            ))

        if lab_metrics.avg_order_to_collect_minutes > 60.0:
            alerts.append(OperationalAlert(
                alert_id="ALT-LAB-COLLECTION-DELAY",
                severity="Warning",
                icon="schedule",
                title="Pre-Analytical Sample Collection Delay",
                message=f"Order-to-collection duration averages {lab_metrics.avg_order_to_collect_minutes} minutes across inpatient wards.",
                category="Turnaround",
                affected_entity="Ward Nursing / Phlebotomy Dispatch",
                recommended_action="Review phlebotomy shift dispatch routes to reduce pre-analytical collection lag.",
                timestamp=now_str
            ))

        if lab_metrics.total_tests_pending > 15:
            alerts.append(OperationalAlert(
                alert_id="ALT-LAB-QUEUE-BACKLOG",
                severity="Warning",
                icon="pending_actions",
                title="Active Diagnostic Queue Backlog",
                message=f"{lab_metrics.total_tests_pending} laboratory test orders are currently pending processing.",
                category="Turnaround",
                affected_entity="Pathology Analyzer Workstations",
                recommended_action="Prioritize urgent orders in analyzer batch queues.",
                timestamp=now_str
            ))

        # ---------------------------------------------------------
        # 3. Data Discrepancy & Missing Reporting Alerts
        # ---------------------------------------------------------
        missing_days_conflicts = [c for c in conflicts if c.category == "MISSING_BED_SHEET_DAY"]
        if missing_days_conflicts:
            missing_dates_str = ", ".join([c.record_ref.split()[1] for c in missing_days_conflicts[:5]])
            alerts.append(OperationalAlert(
                alert_id="ALT-DATA-MISSING-BED-LOGS",
                severity="Warning",
                icon="report_problem",
                title="Missing Daily Nursing Bed Sheets",
                message=f"Manual bed occupancy sheets were omitted for {len(missing_days_conflicts)} dates in July ({missing_dates_str}).",
                category="Missing_Data",
                affected_entity="Nursing Administration",
                recommended_action="MEDLENS has automatically imputed bed census from HIS. Enforce mandatory shift sheet digital submission.",
                timestamp=now_str
            ))

        review_conflicts = [c for c in conflicts if c.resolution_status == "Needs_Review"]
        if review_conflicts:
            alerts.append(OperationalAlert(
                alert_id="ALT-DATA-REVIEW-CONFLICTS",
                severity="Warning",
                icon="rule",
                title="Shift Count Discrepancies Require Audit",
                message=f"{len(review_conflicts)} ward-date occupancy entries showed >2 patient variance between manual bed log and HIS database.",
                category="Data_Discrepancy",
                affected_entity="HIS / Bed Audit Committee",
                recommended_action="Open Reconciliation Explorer to review nursing shift comments and verify discharge clearance lag.",
                timestamp=now_str
            ))

        # ---------------------------------------------------------
        # 4. General Operational Intelligence Alert
        # ---------------------------------------------------------
        alerts.append(OperationalAlert(
            alert_id="ALT-OPS-CENSUS-INFO",
            severity="Info",
            icon="info",
            title="Hospital Operational Status Nominal",
            message=f"{flow_metrics.currently_active_inpatients} active inpatients admitted across {len(bed_metrics.ward_breakdown)} wards. Reconciled data quality: {quality_metrics.overall_quality_score}%.",
            category="Capacity",
            affected_entity="Medicover Hospital Operations",
            recommended_action="Continuous automated reconciliation active.",
            timestamp=now_str
        ))

        # Sort: Critical first, then Warning, then Info
        sev_rank = {"Critical": 0, "Warning": 1, "Info": 2}
        alerts.sort(key=lambda a: sev_rank.get(a.severity, 3))

        return alerts
