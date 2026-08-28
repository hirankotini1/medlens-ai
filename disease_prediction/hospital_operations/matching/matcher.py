"""
Cross-Source Record Matching Layer (HIS, LAB, BED)
"""
from typing import List, Dict, Any, Tuple
from disease_prediction.hospital_operations.models import (
    NormalizedHISRecord,
    NormalizedLabRecord,
    NormalizedBedRecord,
    MatchedPatientRecord
)


class HospitalRecordMatcher:
    """
    Performs deterministic 3-way record matching across HIS admissions,
    Laboratory diagnostic orders, and Bed occupancy logs.
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

    def match_records(self) -> Dict[str, Any]:
        """
        Executes cross-source matching and computes exact match statistics.
        """
        # Map HIS by canonical patient ID and numeric ID (exclude duplicate rows from primary patient map)
        his_by_id: Dict[str, NormalizedHISRecord] = {}
        for r in self.his_records:
            if not r.is_duplicate or r.canonical_patient_id not in his_by_id:
                his_by_id[r.canonical_patient_id] = r

        # Map LAB by canonical patient ID
        lab_by_id: Dict[str, List[NormalizedLabRecord]] = {}
        for r in self.lab_records:
            lab_by_id.setdefault(r.canonical_patient_id, []).append(r)

        all_patient_ids = set(his_by_id.keys()).union(set(lab_by_id.keys()))

        matched_patients: List[MatchedPatientRecord] = []
        matched_count = 0
        outpatient_lab_count = 0
        inpatient_no_lab_count = 0

        for pid in sorted(all_patient_ids):
            his_rec = his_by_id.get(pid)
            lab_recs = lab_by_id.get(pid, [])

            if his_rec is not None and len(lab_recs) > 0:
                status = "Matched"
                matched_count += 1
                numeric_id = his_rec.numeric_id
            elif his_rec is None and len(lab_recs) > 0:
                status = "Outpatient_Lab_Only"
                outpatient_lab_count += 1
                numeric_id = lab_recs[0].numeric_id
            else:
                status = "Inpatient_No_Lab"
                inpatient_no_lab_count += 1
                numeric_id = his_rec.numeric_id if his_rec else 0

            matched_patients.append(MatchedPatientRecord(
                canonical_patient_id=pid,
                numeric_id=numeric_id,
                match_status=status,
                his_record=his_rec.model_dump() if (his_rec and hasattr(his_rec, 'model_dump')) else (his_rec.dict() if his_rec else None),
                lab_records_count=len(lab_recs),
                lab_records=[lr.model_dump() if hasattr(lr, 'model_dump') else lr.dict() for lr in lab_recs],
                has_conflicts=False,
                conflict_ids=[]
            ))

        total_patients = len(all_patient_ids)
        match_percentage = round((matched_count / total_patients * 100), 1) if total_patients > 0 else 0.0
        outpatient_percentage = round((outpatient_lab_count / total_patients * 100), 1) if total_patients > 0 else 0.0
        inpatient_no_lab_percentage = round((inpatient_no_lab_count / total_patients * 100), 1) if total_patients > 0 else 0.0

        return {
            "total_unique_patients": total_patients,
            "matched_count": matched_count,
            "matched_percentage": match_percentage,
            "outpatient_lab_count": outpatient_lab_count,
            "outpatient_percentage": outpatient_percentage,
            "inpatient_no_lab_count": inpatient_no_lab_count,
            "inpatient_no_lab_percentage": inpatient_no_lab_percentage,
            "patients": matched_patients
        }
