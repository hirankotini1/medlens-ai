"""
Data Normalization & Standardization Layer
"""
import re
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from disease_prediction.hospital_operations.models import (
    NormalizedHISRecord,
    NormalizedLabRecord,
    NormalizedBedRecord
)

# Standard Canonical Ward Definitions
CANONICAL_WARDS = {
    "ICU": "Intensive Care Unit (ICU)",
    "MICU": "Medical ICU (MICU)",
    "GEN_WARD_A": "General Ward A",
    "GEN_WARD_B": "General Ward B",
    "PAEDIATRICS": "Paediatrics"
}

WARD_CAPACITIES = {
    "Intensive Care Unit (ICU)": 12,
    "Medical ICU (MICU)": 10,
    "General Ward A": 30,
    "General Ward B": 30,
    "Paediatrics": 16
}

TOTAL_HOSPITAL_BEDS = sum(WARD_CAPACITIES.values())  # 98 beds

# Delay Thresholds in Hours (Configurable)
DELAY_THRESHOLDS = {
    "STAT": {"target_hours": 2.0, "critical_hours": 4.0},
    "URGENT": {"target_hours": 4.0, "critical_hours": 6.0},
    "ROUTINE": {"target_hours": 8.0, "critical_hours": 12.0}
}


class DataStandardizer:
    """
    Standardizes patient identifiers, timestamps, ward names, priorities, and remarks.
    Generates structured normalized records for downstream matching and reconciliation.
    """

    @staticmethod
    def normalize_patient_id(raw_id: Any) -> Tuple[str, int, bool]:
        """
        Returns (canonical_string, numeric_id, is_outpatient).
        e.g., 'MCH-0001001' -> ('MCH-0001001', 1001, False)
              1023 -> ('MCH-0001023', 1023, False)
              7956 -> ('MCH-0007956', 7956, True)
        """
        raw_str = str(raw_id).strip()
        digits = re.sub(r'\D', '', raw_str)
        if not digits:
            num = 0
        else:
            num = int(digits)

        # In our dataset, 7xxx series are outpatients/walk-ins
        is_outpatient = (num >= 7000)

        canonical_str = f"MCH-{num:07d}" if num > 0 else f"MCH-UNKNOWN-{raw_str}"
        return canonical_str, num, is_outpatient

    @staticmethod
    def normalize_ward_name(raw_name: Any) -> str:
        """
        Maps disparate ward spellings and encodings to standard canonical names.
        """
        if not isinstance(raw_name, str) or not raw_name.strip():
            return "General Ward A"

        clean = raw_name.strip().upper().replace('.', '').replace('-', ' ').replace('_', ' ')
        clean = " ".join(clean.split())

        if "MICU" in clean or "MEDICAL ICU" in clean:
            return CANONICAL_WARDS["MICU"]
        elif "ICU" in clean:
            return CANONICAL_WARDS["ICU"]
        elif "GEN WARD A" in clean or "GENERAL WARD A" in clean:
            return CANONICAL_WARDS["GEN_WARD_A"]
        elif "GEN WARD B" in clean or "GENERAL WARD B" in clean:
            return CANONICAL_WARDS["GEN_WARD_B"]
        elif "PAED" in clean or "PED" in clean:
            return CANONICAL_WARDS["PAEDIATRICS"]
        return clean.title()

    @staticmethod
    def normalize_gender(raw_gender: Any) -> str:
        """
        Standardizes gender representations ('m', 'M', 'Male', 'Female', 'f', 'F').
        """
        if not isinstance(raw_gender, str):
            return "Unknown"
        g = raw_gender.strip().upper()
        if g in ['M', 'MALE']:
            return "Male"
        elif g in ['F', 'FEMALE']:
            return "Female"
        return raw_gender.strip().capitalize()

    @staticmethod
    def normalize_priority(raw_priority: Any) -> str:
        """
        Maps priority to 'STAT', 'URGENT', or 'ROUTINE'.
        """
        if not isinstance(raw_priority, str):
            return "ROUTINE"
        p = raw_priority.strip().upper()
        if "STAT" in p:
            return "STAT"
        elif "URG" in p:
            return "URGENT"
        return "ROUTINE"

    @classmethod
    def standardize_his_data(cls, df_his: pd.DataFrame) -> List[NormalizedHISRecord]:
        """
        Standardizes HIS Admissions and Discharges records.
        Detects exact duplicate entries without deleting them.
        """
        records: List[NormalizedHISRecord] = []
        seen_admissions: Dict[Tuple[str, str], int] = {}

        for idx, row in df_his.iterrows():
            raw_pid = str(row['patient_id'])
            canon_pid, num_id, _ = cls.normalize_patient_id(raw_pid)
            raw_ward = str(row['ward'])
            canon_ward = cls.normalize_ward_name(raw_ward)
            dept = str(row['admitting_department']).strip()
            age = int(row['age']) if pd.notnull(row['age']) else 0
            raw_gender = str(row['gender'])
            canon_gender = cls.normalize_gender(raw_gender)

            # Date parsing
            dt_adm = pd.to_datetime(row['admission_datetime'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
            adm_str = dt_adm.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(dt_adm) else str(row['admission_datetime']).strip()

            dt_dis = pd.to_datetime(row['discharge_datetime'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
            dis_str = dt_dis.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(dt_dis) else None
            is_active = (dis_str is None)

            # Duplicate detection key (canonical ID + admission timestamp)
            dup_key = (canon_pid, adm_str)
            is_dup = False
            dup_of = None
            if dup_key in seen_admissions:
                is_dup = True
                dup_of = seen_admissions[dup_key]
            else:
                seen_admissions[dup_key] = idx

            records.append(NormalizedHISRecord(
                row_index=int(idx),
                raw_patient_id=raw_pid,
                canonical_patient_id=canon_pid,
                numeric_id=num_id,
                admission_datetime=adm_str,
                discharge_datetime=dis_str,
                is_active=is_active,
                raw_ward=raw_ward,
                canonical_ward=canon_ward,
                admitting_department=dept,
                age=age,
                raw_gender=raw_gender,
                canonical_gender=canon_gender,
                is_duplicate=is_dup,
                duplicate_of=dup_of
            ))

        return records

    @classmethod
    def standardize_lab_data(cls, df_lab: pd.DataFrame) -> List[NormalizedLabRecord]:
        """
        Standardizes Laboratory order-to-result turnaround records.
        Calculates durations in minutes and classifies delays.
        """
        records: List[NormalizedLabRecord] = []

        for idx, row in df_lab.iterrows():
            order_id = str(row['order_id']).strip()
            raw_pid = str(row['patient_id'])
            canon_pid, num_id, is_outpatient = cls.normalize_patient_id(raw_pid)
            test_name = str(row['test_name']).strip()
            raw_prio = str(row['priority'])
            canon_prio = cls.normalize_priority(raw_prio)
            dept = str(row['department']).strip()

            # Date parsing
            dt_ord = pd.to_datetime(row['ordered_at'], format="%d/%m/%Y %H:%M", errors='coerce')
            dt_col = pd.to_datetime(row['collected_at'], format="%d/%m/%Y %H:%M", errors='coerce')
            dt_res = pd.to_datetime(row['resulted_at'], format="%d/%m/%Y %H:%M", errors='coerce') if pd.notnull(row['resulted_at']) else None

            ord_str = dt_ord.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(dt_ord) else str(row['ordered_at'])
            col_str = dt_col.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(dt_col) else str(row['collected_at'])
            res_str = dt_res.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(dt_res) else None

            # Calculate durations
            order_to_col_min = (dt_col - dt_ord).total_seconds() / 60.0 if (pd.notnull(dt_col) and pd.notnull(dt_ord)) else 0.0
            
            if pd.notnull(dt_res) and pd.notnull(dt_col):
                col_to_res_min = (dt_res - dt_col).total_seconds() / 60.0
                total_tat_min = (dt_res - dt_ord).total_seconds() / 60.0
                status = "Completed"
            else:
                col_to_res_min = None
                total_tat_min = None
                status = "Pending"

            # Delay classification
            is_delayed = False
            delay_severity = None
            if total_tat_min is not None:
                tat_hours = total_tat_min / 60.0
                thresh = DELAY_THRESHOLDS.get(canon_prio, DELAY_THRESHOLDS["ROUTINE"])
                if tat_hours > thresh["critical_hours"]:
                    is_delayed = True
                    delay_severity = "Critical"
                elif tat_hours > thresh["target_hours"]:
                    is_delayed = True
                    delay_severity = "Moderate"

            records.append(NormalizedLabRecord(
                row_index=int(idx),
                order_id=order_id,
                raw_patient_id=raw_pid,
                canonical_patient_id=canon_pid,
                numeric_id=num_id,
                test_name=test_name,
                ordered_at=ord_str,
                collected_at=col_str,
                resulted_at=res_str,
                status=status,
                raw_priority=raw_prio,
                canonical_priority=canon_prio,
                department=dept,
                order_to_collect_minutes=round(order_to_col_min, 1),
                collect_to_result_minutes=round(col_to_res_min, 1) if col_to_res_min is not None else None,
                total_turnaround_minutes=round(total_tat_min, 1) if total_tat_min is not None else None,
                is_delayed=is_delayed,
                delay_severity=delay_severity,
                is_outpatient=is_outpatient
            ))

        return records

    @classmethod
    def standardize_bed_data(cls, df_bed: pd.DataFrame) -> List[NormalizedBedRecord]:
        """
        Standardizes manual Bed Occupancy logs.
        Handles missing Available values and parses contextual nursing remarks.
        """
        records: List[NormalizedBedRecord] = []

        for idx, row in df_bed.iterrows():
            raw_date = str(row['Date'])
            dt_date = pd.to_datetime(raw_date, format="%d-%b-%y", errors='coerce')
            canon_date = dt_date.strftime("%Y-%m-%d") if pd.notnull(dt_date) else raw_date.strip()

            raw_ward = str(row['Ward'])
            canon_ward = cls.normalize_ward_name(raw_ward)

            total_beds = int(row['Total Beds']) if pd.notnull(row['Total Beds']) else WARD_CAPACITIES.get(canon_ward, 30)
            occupied = int(row['Occupied']) if pd.notnull(row['Occupied']) else 0

            raw_avail = float(row['Available']) if pd.notnull(row['Available']) else None
            was_imputed = False
            if raw_avail is None or np.isnan(raw_avail):
                available = max(0, total_beds - occupied)
                was_imputed = True
            else:
                available = int(raw_avail)

            raw_remarks = str(row['Remarks']).strip() if pd.notnull(row['Remarks']) else None
            remarks_lower = raw_remarks.lower() if raw_remarks else ""

            # Parse remarks nuances
            has_daycare = "day-care" in remarks_lower or "daycare" in remarks_lower
            daycare_count = 1 if has_daycare else 0

            pending_dis = 0
            if "discharges pending" in remarks_lower:
                match = re.search(r'(\d+)\s+discharges pending', remarks_lower)
                pending_dis = int(match.group(1)) if match else 2

            is_downtime = "system was down" in remarks_lower or "approx" in remarks_lower

            records.append(NormalizedBedRecord(
                row_index=int(idx),
                raw_date=raw_date,
                canonical_date=canon_date,
                raw_ward=raw_ward,
                canonical_ward=canon_ward,
                total_beds=total_beds,
                occupied=occupied,
                available=available,
                raw_available=raw_avail,
                was_available_imputed=was_imputed,
                remarks=raw_remarks,
                has_daycare=has_daycare,
                daycare_count=daycare_count,
                pending_discharge_count=pending_dis,
                is_system_downtime_approx=is_downtime
            ))

        return records
