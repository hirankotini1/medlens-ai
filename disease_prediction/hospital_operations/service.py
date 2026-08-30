"""
Hospital Operations Service — Master Orchestrator
"""
import os 
import json 
import sqlite3 
from typing import Dict ,Any ,List ,Optional 
from datetime import datetime 

from disease_prediction .hospital_operations .models import (
DataSourceStats ,
NormalizedHISRecord ,
NormalizedLabRecord ,
NormalizedBedRecord ,
ConflictRecord ,
BedCapacityMetrics ,
PatientFlowMetrics ,
LabPerformanceMetrics ,
DataQualityMetrics ,
OperationalAlert ,
UnifiedOperationsOverview 
)
from disease_prediction .hospital_operations .ingestion .loader import HospitalDataLoader 
from disease_prediction .hospital_operations .normalization .standardizer import DataStandardizer 
from disease_prediction .hospital_operations .matching .matcher import HospitalRecordMatcher 
from disease_prediction .hospital_operations .reconciliation .engine import HospitalReconciliationEngine 
from disease_prediction .hospital_operations .reconciliation .rules import get_reconciliation_rules 
from disease_prediction .hospital_operations .metrics .census_metrics import PatientFlowMetricsCalculator 
from disease_prediction .hospital_operations .metrics .bed_metrics import BedCapacityMetricsCalculator 
from disease_prediction .hospital_operations .metrics .lab_metrics import LabPerformanceMetricsCalculator 
from disease_prediction .hospital_operations .metrics .quality_metrics import DataQualityMetricsCalculator 
from disease_prediction .hospital_operations .alerts .alert_engine import HospitalAlertEngine 
from disease_prediction .hospital_operations .reports .daily_report import DailyOperationsReportGenerator 
from disease_prediction .hospital_operations .ai_summary .ops_summarizer import OperationsAISummarizer 


class HospitalOperationsService :
    """
    Singleton service that orchestrates multi-source ingestion, normalization,
    reconciliation, metrics computation, alert generation, and persistence.
    """

    def __init__ (self ,data_dir :str =None ,db_path :str =None ):
        self .loader =HospitalDataLoader (data_dir =data_dir )
        self .db_path =db_path or os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','pathology.db'))
        self ._cached_overview :Optional [UnifiedOperationsOverview ]=None 
        self ._cached_conflicts :Optional [List [ConflictRecord ]]=None 
        self ._cached_matching :Optional [Dict [str ,Any ]]=None 
        self ._cached_sources :Optional [Dict [str ,DataSourceStats ]]=None 
        self ._cached_his :Optional [List [NormalizedHISRecord ]]=None 
        self ._cached_lab :Optional [List [NormalizedLabRecord ]]=None 
        self ._cached_bed :Optional [List [NormalizedBedRecord ]]=None 

        self ._init_history_table ()

    def _init_history_table (self ):
        """Creates operations run history table in SQLite if not exists."""
        try :
            conn =sqlite3 .connect (self .db_path )
            cursor =conn .cursor ()
            cursor .execute ("""
            CREATE TABLE IF NOT EXISTS operations_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                total_records_processed INTEGER NOT NULL,
                active_inpatients INTEGER NOT NULL,
                bed_occupancy_pct REAL NOT NULL,
                avg_lab_tat_hours REAL NOT NULL,
                quality_score REAL NOT NULL,
                conflicts_count INTEGER NOT NULL,
                resolved_conflicts_count INTEGER NOT NULL,
                overview_json TEXT NOT NULL
            );
            """)
            conn .commit ()
            conn .close ()
        except Exception as e :
            print (f"[OPS-SERVICE-INIT-WARN] Could not initialize operations_runs table: {e }")

    def run_reconciliation_pipeline (self ,force_refresh :bool =False )->UnifiedOperationsOverview :
        """
        Executes the full end-to-end data intake, standardization, matching,
        reconciliation, and metrics calculation workflow.
        """
        if self ._cached_overview and not force_refresh :
            return self ._cached_overview 


        df_his ,df_lab ,df_bed =self .loader .load_raw_dataframes ()
        self ._cached_sources =self .loader .get_source_statistics ()


        self ._cached_his =DataStandardizer .standardize_his_data (df_his )
        self ._cached_lab =DataStandardizer .standardize_lab_data (df_lab )
        self ._cached_bed =DataStandardizer .standardize_bed_data (df_bed )


        matcher =HospitalRecordMatcher (self ._cached_his ,self ._cached_lab ,self ._cached_bed )
        self ._cached_matching =matcher .match_records ()


        recon_engine =HospitalReconciliationEngine (self ._cached_his ,self ._cached_lab ,self ._cached_bed )
        recon_result =recon_engine .execute_reconciliation ()
        self ._cached_conflicts =recon_result ["conflicts"]


        flow_metrics =PatientFlowMetricsCalculator .calculate_metrics (self ._cached_his )
        bed_metrics =BedCapacityMetricsCalculator .calculate_metrics (self ._cached_bed ,self ._cached_his )
        lab_metrics =LabPerformanceMetricsCalculator .calculate_metrics (self ._cached_lab )
        quality_metrics =DataQualityMetricsCalculator .calculate_metrics (
        self ._cached_his ,self ._cached_lab ,self ._cached_bed ,self ._cached_conflicts 
        )


        alerts =HospitalAlertEngine .generate_alerts (
        bed_metrics ,lab_metrics ,flow_metrics ,quality_metrics ,self ._cached_conflicts 
        )

        critical_count =sum (1 for a in alerts if a .severity =="Critical")
        now_str =datetime .now ().strftime ("%Y-%m-%d %H:%M:%S")


        overview =UnifiedOperationsOverview (
        timestamp =now_str ,
        active_inpatient_census =flow_metrics .currently_active_inpatients ,
        bed_occupancy_percentage =bed_metrics .overall_occupancy_percentage ,
        total_beds_occupied =bed_metrics .total_occupied_beds ,
        total_beds_available =bed_metrics .total_available_beds ,
        total_hospital_capacity =bed_metrics .total_hospital_beds ,
        lab_turnaround_avg_hours =lab_metrics .overall_avg_turnaround_hours ,
        lab_pending_tests_count =lab_metrics .total_tests_pending ,
        stat_turnaround_avg_hours =lab_metrics .priority_performance .get ("STAT",{}).get ("avg_turnaround_hours",0.0 ),
        critical_alerts_count =critical_count ,
        total_conflicts_count =len (self ._cached_conflicts ),
        data_quality_score =quality_metrics .overall_quality_score ,
        quick_status_summary =(
        f"{flow_metrics .currently_active_inpatients } active inpatients | "
        f"{bed_metrics .overall_occupancy_percentage }% bed capacity | "
        f"Lab TAT {lab_metrics .overall_avg_turnaround_hours }h | "
        f"Quality Score {quality_metrics .overall_quality_score }%"
        ),
        top_alerts =alerts ,
        bed_capacity =bed_metrics ,
        patient_flow =flow_metrics ,
        lab_performance =lab_metrics ,
        data_quality =quality_metrics 
        )

        self ._cached_overview =overview 
        self ._record_run_history (overview )

        return overview 

    def _record_run_history (self ,overview :UnifiedOperationsOverview ):
        """Persists run metrics to the SQLite audit ledger."""
        try :
            conn =sqlite3 .connect (self .db_path )
            cursor =conn .cursor ()
            run_id =f"RUN-{datetime .now ().strftime ('%Y%m%d-%H%M%S')}"
            overview_json_str =overview .model_dump_json ()if hasattr (overview ,'model_dump_json')else overview .json ()
            cursor .execute ("""
            INSERT INTO operations_runs (
                run_id, timestamp, total_records_processed, active_inpatients,
                bed_occupancy_pct, avg_lab_tat_hours, quality_score,
                conflicts_count, resolved_conflicts_count, overview_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,(
            run_id ,
            overview .timestamp ,
            overview .data_quality .total_records_processed ,
            overview .active_inpatient_census ,
            overview .bed_occupancy_percentage ,
            overview .lab_turnaround_avg_hours ,
            overview .data_quality_score ,
            overview .total_conflicts_count ,
            overview .data_quality .resolved_conflicts_count ,
            overview_json_str 
            ))
            conn .commit ()
            conn .close ()
        except Exception as e :
            print (f"[OPS-HISTORY-PERSIST-WARN] {e }")

    def get_sources_info (self )->Dict [str ,Any ]:
        self .run_reconciliation_pipeline ()
        return {
        "sources":{k :(v .model_dump ()if hasattr (v ,'model_dump')else v .dict ())for k ,v in self ._cached_sources .items ()},
        "total_records":sum (s .total_records for s in self ._cached_sources .values ())
        }

    def get_conflicts_data (self ,category :Optional [str ]=None ,severity :Optional [str ]=None )->Dict [str ,Any ]:
        self .run_reconciliation_pipeline ()
        conflicts =self ._cached_conflicts or []
        if category :
            conflicts =[c for c in conflicts if c .category ==category ]
        if severity :
            conflicts =[c for c in conflicts if c .severity ==severity ]

        return {
        "total_conflicts":len (self ._cached_conflicts ),
        "filtered_count":len (conflicts ),
        "resolved_count":sum (1 for c in self ._cached_conflicts if c .resolution_status =="Resolved"),
        "needs_review_count":sum (1 for c in self ._cached_conflicts if c .resolution_status =="Needs_Review"),
        "conflicts":[(c .model_dump ()if hasattr (c ,'model_dump')else c .dict ())for c in conflicts ]
        }

    def get_conflict_by_id (self ,conflict_id :str )->Optional [Dict [str ,Any ]]:
        self .run_reconciliation_pipeline ()
        for c in self ._cached_conflicts :
            if c .conflict_id ==conflict_id :
                return c .model_dump ()if hasattr (c ,'model_dump')else c .dict ()
        return None 

    def get_rules_catalog (self )->List [Dict [str ,Any ]]:
        return [(r .model_dump ()if hasattr (r ,'model_dump')else r .dict ())for r in get_reconciliation_rules ()]

    def get_source_comparison_matrix (self )->Dict [str ,Any ]:
        """
        Builds a comprehensive source comparison matrix showing HIS vs BED vs LAB.
        """
        self .run_reconciliation_pipeline ()
        return {
        "sources":["HIS Admissions & Discharges","Lab Order-to-Result","Manual Bed Occupancy"],
        "matching_summary":self ._cached_matching ,
        "wards_comparison":self ._cached_overview .bed_capacity .ward_breakdown ,
        "discrepancies_sample":[(c .model_dump ()if hasattr (c ,'model_dump')else c .dict ())for c in self ._cached_conflicts [:15 ]]
        }

    def get_daily_report_html (self )->str :
        overview =self .run_reconciliation_pipeline ()
        return DailyOperationsReportGenerator .generate_html_report (overview )

    def get_daily_report_csv (self )->str :
        overview =self .run_reconciliation_pipeline ()
        return DailyOperationsReportGenerator .generate_csv_summary (overview )

    def get_ai_summary (self )->Dict [str ,Any ]:
        overview =self .run_reconciliation_pipeline ()
        return OperationsAISummarizer .generate_summary (overview )

    def get_operations_history (self ,limit :int =20 )->List [Dict [str ,Any ]]:
        try :
            conn =sqlite3 .connect (self .db_path )
            conn .row_factory =sqlite3 .Row 
            cursor =conn .cursor ()
            cursor .execute ("""
            SELECT run_id, timestamp, total_records_processed, active_inpatients,
                   bed_occupancy_pct, avg_lab_tat_hours, quality_score,
                   conflicts_count, resolved_conflicts_count
            FROM operations_runs
            ORDER BY id DESC
            LIMIT ?
            """,(limit ,))
            rows =cursor .fetchall ()
            conn .close ()
            return [dict (r )for r in rows ]
        except Exception as e :
            return []
