"""
MEDLENS Hospital Operations Intelligence — Data Models & Schemas
"""
from typing import Optional ,List ,Dict ,Any 
from pydantic import BaseModel ,Field 
from datetime import datetime 


class DataSourceStats (BaseModel ):
    source_name :str 
    file_name :str 
    file_path :str 
    total_records :int 
    date_range_start :Optional [str ]=None 
    date_range_end :Optional [str ]=None 
    missing_values_count :int 
    missing_fields_breakdown :Dict [str ,int ]
    duplicate_records_count :int 
    processing_status :str 
    last_processed :str 
    raw_columns :List [str ]


class NormalizedHISRecord (BaseModel ):
    row_index :int 
    raw_patient_id :str 
    canonical_patient_id :str 
    numeric_id :int 
    admission_datetime :str 
    discharge_datetime :Optional [str ]=None 
    is_active :bool 
    raw_ward :str 
    canonical_ward :str 
    admitting_department :str 
    age :int 
    raw_gender :str 
    canonical_gender :str 
    is_duplicate :bool =False 
    duplicate_of :Optional [int ]=None 


class NormalizedLabRecord (BaseModel ):
    row_index :int 
    order_id :str 
    raw_patient_id :str 
    canonical_patient_id :str 
    numeric_id :int 
    test_name :str 
    ordered_at :str 
    collected_at :str 
    resulted_at :Optional [str ]=None 
    status :str 
    raw_priority :str 
    canonical_priority :str 
    department :str 
    order_to_collect_minutes :float 
    collect_to_result_minutes :Optional [float ]=None 
    total_turnaround_minutes :Optional [float ]=None 
    is_delayed :bool =False 
    delay_severity :Optional [str ]=None 
    is_outpatient :bool =False 


class NormalizedBedRecord (BaseModel ):
    row_index :int 
    raw_date :str 
    canonical_date :str 
    raw_ward :str 
    canonical_ward :str 
    total_beds :int 
    occupied :int 
    available :int 
    raw_available :Optional [float ]=None 
    was_available_imputed :bool =False 
    remarks :Optional [str ]=None 
    has_daycare :bool =False 
    daycare_count :int =0 
    pending_discharge_count :int =0 
    is_system_downtime_approx :bool =False 


class MatchedPatientRecord (BaseModel ):
    canonical_patient_id :str 
    numeric_id :int 
    match_status :str 
    his_record :Optional [Dict [str ,Any ]]=None 
    lab_records_count :int =0 
    lab_records :List [Dict [str ,Any ]]=[]
    has_conflicts :bool =False 
    conflict_ids :List [str ]=[]


class ConflictRecord (BaseModel ):
    conflict_id :str 
    category :str 
    source_a :str 
    source_b :Optional [str ]=None 
    record_ref :str 
    source_a_value :Any 
    source_b_value :Optional [Any ]=None 
    difference_summary :str 
    applied_rule_id :str 
    applied_rule_name :str 
    resolution_status :str 
    reconciled_value :Any 
    explanation_reason :str 
    severity :str 
    timestamp :str 


class ReconciliationRuleDef (BaseModel ):
    rule_id :str 
    rule_name :str 
    category :str 
    primary_source :str 
    secondary_source :Optional [str ]=None 
    description :str 
    rationale :str 
    action_taken :str 


class BedCapacityMetrics (BaseModel ):
    total_hospital_beds :int 
    total_occupied_beds :int 
    total_available_beds :int 
    overall_occupancy_percentage :float 
    overall_status :str 
    ward_breakdown :List [Dict [str ,Any ]]
    date_trend :List [Dict [str ,Any ]]
    configured_warning_threshold :float =80.0 
    configured_critical_threshold :float =90.0 


class PatientFlowMetrics (BaseModel ):
    total_admissions :int 
    total_discharges :int 
    currently_active_inpatients :int 
    average_length_of_stay_days :float 
    department_distribution :Dict [str ,int ]
    ward_distribution :Dict [str ,int ]
    gender_distribution :Dict [str ,int ]
    age_group_distribution :Dict [str ,int ]
    daily_admissions_discharges_timeline :List [Dict [str ,Any ]]


class LabPerformanceMetrics (BaseModel ):
    total_tests_ordered :int 
    total_tests_completed :int 
    total_tests_pending :int 
    completion_rate_percentage :float 
    overall_avg_turnaround_hours :float 
    overall_median_turnaround_hours :float 
    longest_turnaround_hours :float 
    avg_order_to_collect_minutes :float 
    avg_collect_to_result_hours :float 
    priority_performance :Dict [str ,Dict [str ,Any ]]
    test_performance :Dict [str ,Dict [str ,Any ]]
    department_performance :Dict [str ,Dict [str ,Any ]]
    delayed_tests_count :int 
    delayed_tests_breakdown :Dict [str ,int ]
    pending_queue_sample :List [Dict [str ,Any ]]


class DataQualityMetrics (BaseModel ):
    overall_quality_score :float 
    rating :str 
    total_records_processed :int 
    total_conflicts_detected :int 
    resolved_conflicts_count :int 
    pending_review_conflicts_count :int 
    duplicates_detected :int 
    missing_values_handled :int 
    date_normalizations_count :int 
    unmatched_outpatient_records :int 
    penalties_breakdown :List [Dict [str ,Any ]]
    calculation_methodology :str 


class OperationalAlert (BaseModel ):
    alert_id :str 
    severity :str 
    icon :str 
    title :str 
    message :str 
    category :str 
    affected_entity :str 
    recommended_action :str 
    timestamp :str 


class UnifiedOperationsOverview (BaseModel ):
    timestamp :str 
    active_inpatient_census :int 
    bed_occupancy_percentage :float 
    total_beds_occupied :int 
    total_beds_available :int 
    total_hospital_capacity :int 
    lab_turnaround_avg_hours :float 
    lab_pending_tests_count :int 
    stat_turnaround_avg_hours :float 
    critical_alerts_count :int 
    total_conflicts_count :int 
    data_quality_score :float 
    quick_status_summary :str 
    top_alerts :List [OperationalAlert ]
    bed_capacity :BedCapacityMetrics 
    patient_flow :PatientFlowMetrics 
    lab_performance :LabPerformanceMetrics 
    data_quality :DataQualityMetrics 
