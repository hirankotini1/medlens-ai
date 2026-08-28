"""
Data Ingestion Layer for Hospital Operations Sources
"""
import os
import pandas as pd
from typing import Tuple, Dict, Any
from datetime import datetime
from disease_prediction.hospital_operations.models import DataSourceStats

class HospitalDataLoader:
    """
    Safely discovers, reads, and validates the three official hackathon CSV data sources.
    Tracks raw metrics, null counts, duplicate rows, and schema integrity.
    """

    def __init__(self, data_dir: str = None):
        if not data_dir:
            # Fallback path checks
            candidates = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'datasets', 'hospital_operations')),
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'medicover data')),
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'medicover data')),
                r"c:\Users\91797\Downloads\uday hospital\medicover data"
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.exists(os.path.join(cand, '01_his_admissions_discharges.csv')):
                    data_dir = cand
                    break
        
        self.data_dir = data_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'datasets', 'hospital_operations'))
        self.his_file = os.path.join(self.data_dir, '01_his_admissions_discharges.csv')
        self.lab_file = os.path.join(self.data_dir, '02_lab_order_to_result.csv')
        self.bed_file = os.path.join(self.data_dir, '03_bed_occupancy_manual.csv')

    def load_raw_dataframes(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Reads the 3 CSV files without modifying original data.
        """
        if not os.path.exists(self.his_file):
            raise FileNotFoundError(f"HIS file not found at: {self.his_file}")
        if not os.path.exists(self.lab_file):
            raise FileNotFoundError(f"Lab file not found at: {self.lab_file}")
        if not os.path.exists(self.bed_file):
            raise FileNotFoundError(f"Bed file not found at: {self.bed_file}")

        df_his = pd.read_csv(self.his_file)
        df_lab = pd.read_csv(self.lab_file)
        df_bed = pd.read_csv(self.bed_file)

        return df_his, df_lab, df_bed

    def get_source_statistics(self) -> Dict[str, DataSourceStats]:
        """
        Computes accurate, un-hardcoded intake statistics for all three sources.
        """
        df_his, df_lab, df_bed = self.load_raw_dataframes()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. HIS Stats
        his_nulls = df_his.isnull().sum().to_dict()
        his_dups = int(df_his.duplicated().sum())
        his_dates = pd.to_datetime(df_his['admission_datetime'], errors='coerce')
        his_start = his_dates.min().strftime("%Y-%m-%d") if not his_dates.empty else None
        his_end = his_dates.max().strftime("%Y-%m-%d") if not his_dates.empty else None

        his_stats = DataSourceStats(
            source_name="HIS Admissions & Discharges",
            file_name=os.path.basename(self.his_file),
            file_path=self.his_file,
            total_records=len(df_his),
            date_range_start=his_start,
            date_range_end=his_end,
            missing_values_count=int(df_his.isnull().sum().sum()),
            missing_fields_breakdown={k: int(v) for k, v in his_nulls.items() if v > 0},
            duplicate_records_count=his_dups,
            processing_status="Processed",
            last_processed=now_str,
            raw_columns=list(df_his.columns)
        )

        # 2. LAB Stats
        lab_nulls = df_lab.isnull().sum().to_dict()
        lab_dups = int(df_lab.duplicated().sum())
        lab_dates = pd.to_datetime(df_lab['ordered_at'], format="%d/%m/%Y %H:%M", errors='coerce')
        lab_start = lab_dates.min().strftime("%Y-%m-%d") if not lab_dates.empty else None
        lab_end = lab_dates.max().strftime("%Y-%m-%d") if not lab_dates.empty else None

        lab_stats = DataSourceStats(
            source_name="Lab Order-to-Result",
            file_name=os.path.basename(self.lab_file),
            file_path=self.lab_file,
            total_records=len(df_lab),
            date_range_start=lab_start,
            date_range_end=lab_end,
            missing_values_count=int(df_lab.isnull().sum().sum()),
            missing_fields_breakdown={k: int(v) for k, v in lab_nulls.items() if v > 0},
            duplicate_records_count=lab_dups,
            processing_status="Processed",
            last_processed=now_str,
            raw_columns=list(df_lab.columns)
        )

        # 3. BED Stats
        bed_nulls = df_bed.isnull().sum().to_dict()
        bed_dups = int(df_bed.duplicated().sum())
        bed_dates = pd.to_datetime(df_bed['Date'], format="%d-%b-%y", errors='coerce')
        bed_start = bed_dates.min().strftime("%Y-%m-%d") if not bed_dates.empty else None
        bed_end = bed_dates.max().strftime("%Y-%m-%d") if not bed_dates.empty else None

        bed_stats = DataSourceStats(
            source_name="Manual Bed Occupancy Sheet",
            file_name=os.path.basename(self.bed_file),
            file_path=self.bed_file,
            total_records=len(df_bed),
            date_range_start=bed_start,
            date_range_end=bed_end,
            missing_values_count=int(df_bed.isnull().sum().sum()),
            missing_fields_breakdown={k: int(v) for k, v in bed_nulls.items() if v > 0},
            duplicate_records_count=bed_dups,
            processing_status="Processed",
            last_processed=now_str,
            raw_columns=list(df_bed.columns)
        )

        return {
            "his": his_stats,
            "lab": lab_stats,
            "bed": bed_stats
        }
