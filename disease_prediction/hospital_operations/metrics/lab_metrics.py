"""
Laboratory Turnaround & Performance Metrics Calculator
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from disease_prediction.hospital_operations.models import (
    NormalizedLabRecord,
    LabPerformanceMetrics
)


class LabPerformanceMetricsCalculator:
    """
    Computes diagnostic laboratory turnaround times, order-to-collection delay,
    priority prioritization disparities, and bottleneck patterns.
    """

    @staticmethod
    def calculate_metrics(lab_records: List[NormalizedLabRecord]) -> LabPerformanceMetrics:
        total_ordered = len(lab_records)
        completed_records = [r for r in lab_records if r.status == "Completed" and r.total_turnaround_minutes is not None]
        pending_records = [r for r in lab_records if r.status == "Pending"]

        total_completed = len(completed_records)
        total_pending = len(pending_records)
        completion_rate = round((total_completed / total_ordered * 100), 1) if total_ordered > 0 else 0.0

        # Turnaround in hours
        tats_hours = [r.total_turnaround_minutes / 60.0 for r in completed_records]
        avg_tat = round(float(np.mean(tats_hours)), 2) if tats_hours else 0.0
        median_tat = round(float(np.median(tats_hours)), 2) if tats_hours else 0.0
        longest_tat = round(float(np.max(tats_hours)), 2) if tats_hours else 0.0

        # Phase breakdowns
        order_to_cols = [r.order_to_collect_minutes for r in lab_records]
        avg_order_to_col = round(float(np.mean(order_to_cols)), 1) if order_to_cols else 0.0

        col_to_res = [r.collect_to_result_minutes / 60.0 for r in completed_records if r.collect_to_result_minutes is not None]
        avg_col_to_res = round(float(np.mean(col_to_res)), 2) if col_to_res else 0.0

        # Priority Performance
        priority_perf: Dict[str, Dict[str, Any]] = {}
        for p in ["STAT", "URGENT", "ROUTINE"]:
            p_recs = [r for r in completed_records if r.canonical_priority == p]
            p_pending = [r for r in pending_records if r.canonical_priority == p]
            p_tats = [r.total_turnaround_minutes / 60.0 for r in p_recs]

            priority_perf[p] = {
                "total_orders": len(p_recs) + len(p_pending),
                "completed": len(p_recs),
                "pending": len(p_pending),
                "avg_turnaround_hours": round(float(np.mean(p_tats)), 2) if p_tats else 0.0,
                "median_turnaround_hours": round(float(np.median(p_tats)), 2) if p_tats else 0.0,
                "min_turnaround_hours": round(float(np.min(p_tats)), 2) if p_tats else 0.0,
                "max_turnaround_hours": round(float(np.max(p_tats)), 2) if p_tats else 0.0,
                "delayed_count": sum(1 for r in p_recs if r.is_delayed)
            }

        # Test-wise Performance
        test_perf: Dict[str, Dict[str, Any]] = {}
        test_names = sorted(list(set(r.test_name for r in lab_records)))
        for t in test_names:
            t_recs = [r for r in completed_records if r.test_name == t]
            t_pending = [r for r in pending_records if r.test_name == t]
            t_tats = [r.total_turnaround_minutes / 60.0 for r in t_recs]
            test_perf[t] = {
                "total_orders": len(t_recs) + len(t_pending),
                "completed": len(t_recs),
                "pending": len(t_pending),
                "avg_turnaround_hours": round(float(np.mean(t_tats)), 2) if t_tats else 0.0,
                "median_turnaround_hours": round(float(np.median(t_tats)), 2) if t_tats else 0.0
            }

        # Department Performance
        dept_perf: Dict[str, Dict[str, Any]] = {}
        depts = sorted(list(set(r.department for r in lab_records)))
        for d in depts:
            d_recs = [r for r in completed_records if r.department == d]
            d_pending = [r for r in pending_records if r.department == d]
            d_tats = [r.total_turnaround_minutes / 60.0 for r in d_recs]
            dept_perf[d] = {
                "total_orders": len(d_recs) + len(d_pending),
                "completed": len(d_recs),
                "pending": len(d_pending),
                "avg_turnaround_hours": round(float(np.mean(d_tats)), 2) if d_tats else 0.0
            }

        # Delayed test totals
        delayed_recs = [r for r in completed_records if r.is_delayed]
        delayed_breakdown = {
            "STAT (>4h)": sum(1 for r in delayed_recs if r.canonical_priority == "STAT" and r.delay_severity == "Critical"),
            "URGENT (>6h)": sum(1 for r in delayed_recs if r.canonical_priority == "URGENT" and r.delay_severity == "Critical"),
            "ROUTINE (>12h)": sum(1 for r in delayed_recs if r.canonical_priority == "ROUTINE" and r.delay_severity == "Critical"),
            "Moderate Delays": sum(1 for r in delayed_recs if r.delay_severity == "Moderate")
        }

        # Pending Queue sample
        pending_queue = [
            {
                "order_id": r.order_id,
                "patient_id": r.canonical_patient_id,
                "test_name": r.test_name,
                "priority": r.canonical_priority,
                "department": r.department,
                "ordered_at": r.ordered_at,
                "collected_at": r.collected_at,
                "is_outpatient": r.is_outpatient
            }
            for r in pending_records
        ]

        return LabPerformanceMetrics(
            total_tests_ordered=total_ordered,
            total_tests_completed=total_completed,
            total_tests_pending=total_pending,
            completion_rate_percentage=completion_rate,
            overall_avg_turnaround_hours=avg_tat,
            overall_median_turnaround_hours=median_tat,
            longest_turnaround_hours=longest_tat,
            avg_order_to_collect_minutes=avg_order_to_col,
            avg_collect_to_result_hours=avg_col_to_res,
            priority_performance=priority_perf,
            test_performance=test_perf,
            department_performance=dept_perf,
            delayed_tests_count=len(delayed_recs),
            delayed_tests_breakdown=delayed_breakdown,
            pending_queue_sample=pending_queue
        )
