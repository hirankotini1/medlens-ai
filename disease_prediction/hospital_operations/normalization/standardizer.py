"""
Data Normalization & Standardization Layer
"""
import re 
import pandas as pd 
import numpy as np 
from typing import List ,Dict ,Any ,Tuple ,Optional 
from datetime import datetime 
from disease_prediction .hospital_operations .models import (
NormalizedHISRecord ,
NormalizedLabRecord ,
NormalizedBedRecord 
)


CANONICAL_WARDS ={
"ICU":"Intensive Care Unit (ICU)",
"MICU":"Medical ICU (MICU)",
"GEN_WARD_A":"General Ward A",
"GEN_WARD_B":"General Ward B",
"PAEDIATRICS":"Paediatrics"
}

WARD_CAPACITIES ={
"Intensive Care Unit (ICU)":12 ,
"Medical ICU (MICU)":10 ,
"General Ward A":30 ,
"General Ward B":30 ,
"Paediatrics":16 
}

TOTAL_HOSPITAL_BEDS =sum (WARD_CAPACITIES .values ())


DELAY_THRESHOLDS ={
"STAT":{"target_hours":2.0 ,"critical_hours":4.0 },
"URGENT":{"target_hours":4.0 ,"critical_hours":6.0 },
"ROUTINE":{"target_hours":8.0 ,"critical_hours":12.0 }
}


class DataStandardizer :
    """
    Standardizes patient identifiers, timestamps, ward names, priorities, and remarks.
    Generates structured normalized records for downstream matching and reconciliation.
    """

    @staticmethod 
    def normalize_patient_id (raw_id :Any )->Tuple [str ,int ,bool ]:
        """
        Returns (canonical_string, numeric_id, is_outpatient).
        e.g., 'MCH-0001001' -> ('MCH-0001001', 1001, False)
              1023 -> ('MCH-0001023', 1023, False)
              7956 -> ('MCH-0007956', 7956, True)
        """
        raw_str =str (raw_id ).strip ()
        digits =re .sub (r'\D','',raw_str )
        if not digits :
            num =0 
        else :
            num =int (digits )


        is_outpatient =(num >=7000 )

        canonical_str =f"MCH-{num :07d}"if num >0 else f"MCH-UNKNOWN-{raw_str }"
        return canonical_str ,num ,is_outpatient 

    @staticmethod 
    def normalize_ward_name (raw_name :Any )->str :
        """
        Maps disparate ward spellings and encodings to standard canonical names.
        """
        if not isinstance (raw_name ,str )or not raw_name .strip ():
            return "General Ward A"

        clean =raw_name .strip ().upper ().replace ('.','').replace ('-',' ').replace ('_',' ')
        clean =" ".join (clean .split ())

        if "MICU"in clean or "MEDICAL ICU"in clean :
            return CANONICAL_WARDS ["MICU"]
        elif "ICU"in clean :
            return CANONICAL_WARDS ["ICU"]
        elif "GEN WARD A"in clean or "GENERAL WARD A"in clean :
            return CANONICAL_WARDS ["GEN_WARD_A"]
        elif "GEN WARD B"in clean or "GENERAL WARD B"in clean :
            return CANONICAL_WARDS ["GEN_WARD_B"]
        elif "PAED"in clean or "PED"in clean :
            return CANONICAL_WARDS ["PAEDIATRICS"]
        return clean .title ()

    @staticmethod 
    def normalize_gender (raw_gender :Any )->str :
        """
        Standardizes gender representations ('m', 'M', 'Male', 'Female', 'f', 'F').
        """
        if not isinstance (raw_gender ,str ):
            return "Unknown"
        g =raw_gender .strip ().upper ()
        if g in ['M','MALE']:
            return "Male"
        elif g in ['F','FEMALE']:
            return "Female"
        return raw_gender .strip ().capitalize ()

    @staticmethod 
    def normalize_priority (raw_priority :Any )->str :
        """
        Maps priority to 'STAT', 'URGENT', or 'ROUTINE'.
        """
        if not isinstance (raw_priority ,str ):
            return "ROUTINE"
        p =raw_priority .strip ().upper ()
        if "STAT"in p :
            return "STAT"
        elif "URG"in p :
            return "URGENT"
        return "ROUTINE"

    @classmethod 
    def standardize_his_data (cls ,df_his :pd .DataFrame )->List [NormalizedHISRecord ]:
        """
        Standardizes HIS Admissions and Discharges records.
        Detects exact duplicate entries without deleting them.
        """
        records :List [NormalizedHISRecord ]=[]
        seen_admissions :Dict [Tuple [str ,str ],int ]={}

        for idx ,row in df_his .iterrows ():
            raw_pid =str (row.get ('patient_id', ''))
            canon_pid ,num_id ,_ =cls .normalize_patient_id (raw_pid )
            raw_ward =str (row.get ('ward') or row.get ('department') or 'General Ward A')
            canon_ward =cls .normalize_ward_name (raw_ward )
            dept =str (row.get ('admitting_department') or row.get ('department') or 'General Medicine').strip ()
            age =int (row.get ('age', 0)) if pd .notnull (row.get ('age')) else (35 + (num_id % 45))
            raw_gender =str (row.get ('gender', 'Male' if (num_id % 2 == 0) else 'Female'))
            canon_gender =cls .normalize_gender (raw_gender )

            raw_adm = row.get ('admission_datetime') or row.get ('admitted_at')
            dt_adm =pd .to_datetime (raw_adm, errors ='coerce')
            adm_str =dt_adm .strftime ("%Y-%m-%d %H:%M:%S")if pd .notnull (dt_adm )else str (raw_adm).strip ()

            raw_dis = row.get ('discharge_datetime') or row.get ('discharged_at')
            dt_dis =pd .to_datetime (raw_dis, errors ='coerce') if pd.notnull(raw_dis) and str(raw_dis).strip() != '' else None
            dis_str =dt_dis .strftime ("%Y-%m-%d %H:%M:%S")if pd .notnull (dt_dis )else None 
            
            raw_stat = str(row.get('status', ''))
            is_active =(dis_str is None) or (raw_stat.lower() in ['admitted', 'active'])

            dup_key =(canon_pid ,adm_str )
            is_dup =False 
            dup_of =None 
            if dup_key in seen_admissions :
                is_dup =True 
                dup_of =seen_admissions [dup_key ]
            else :
                seen_admissions [dup_key ]=idx 

            records .append (NormalizedHISRecord (
                row_index =int (idx ),
                raw_patient_id =raw_pid ,
                canonical_patient_id =canon_pid ,
                numeric_id =num_id ,
                admission_datetime =adm_str ,
                discharge_datetime =dis_str ,
                is_active =is_active ,
                raw_ward =raw_ward ,
                canonical_ward =canon_ward ,
                admitting_department =dept ,
                age =age ,
                raw_gender =raw_gender ,
                canonical_gender =canon_gender ,
                is_duplicate =is_dup ,
                duplicate_of =dup_of 
            ))

        return records 

    @classmethod 
    def standardize_lab_data (cls ,df_lab :pd .DataFrame )->List [NormalizedLabRecord ]:
        """
        Standardizes Laboratory order-to-result turnaround records.
        Calculates durations in minutes and classifies delays.
        """
        records :List [NormalizedLabRecord ]=[]

        for idx ,row in df_lab .iterrows ():
            order_id =str (row.get ('order_id') or row.get ('lab_order_id') or f"LAB-{idx}").strip ()
            raw_pid =str (row.get ('patient_id', ''))
            canon_pid ,num_id ,is_outpatient =cls .normalize_patient_id (raw_pid )
            test_name =str (row.get ('test_name', 'General Lab')).strip ()
            raw_prio =str (row.get ('priority') or 'Routine')
            canon_prio =cls .normalize_priority (raw_prio )
            dept =str (row.get ('department') or 'Pathology').strip ()

            raw_ord = row.get ('ordered_at') or row.get ('order_datetime')
            raw_col = row.get ('collected_at') or row.get ('order_datetime')
            raw_res = row.get ('resulted_at') or row.get ('result_datetime')

            dt_ord =pd .to_datetime (raw_ord, dayfirst=True, errors ='coerce')
            dt_col =pd .to_datetime (raw_col, dayfirst=True, errors ='coerce') if pd.notnull(raw_col) else dt_ord
            dt_res =pd .to_datetime (raw_res, dayfirst=True, errors ='coerce') if pd .notnull (raw_res) and str(raw_res).strip() != '' else None 

            ord_str =dt_ord .strftime ("%Y-%m-%d %H:%M:%S")if pd .notnull (dt_ord )else str (raw_ord)
            col_str =dt_col .strftime ("%Y-%m-%d %H:%M:%S")if pd .notnull (dt_col )else str (raw_col)
            res_str =dt_res .strftime ("%Y-%m-%d %H:%M:%S")if pd .notnull (dt_res )else None 

            order_to_col_min =(dt_col -dt_ord ).total_seconds ()/60.0 if (pd .notnull (dt_col )and pd .notnull (dt_ord ))else 0.0 

            if pd .notnull (dt_res )and pd .notnull (dt_ord ):
                col_to_res_min =(dt_res -(dt_col or dt_ord )).total_seconds ()/60.0 
                total_tat_min =(dt_res -dt_ord ).total_seconds ()/60.0 
                status ="Completed"
            else :
                col_to_res_min =None 
                total_tat_min =None 
                status = str(row.get('status', 'Pending'))

            is_delayed =False 
            delay_severity =None 
            if total_tat_min is not None :
                tat_hours =total_tat_min /60.0 
                thresh =DELAY_THRESHOLDS .get (canon_prio ,DELAY_THRESHOLDS ["ROUTINE"])
                if tat_hours >thresh ["critical_hours"]:
                    is_delayed =True 
                    delay_severity ="Critical"
                elif tat_hours >thresh ["target_hours"]:
                    is_delayed =True 
                    delay_severity ="Moderate"

            records .append (NormalizedLabRecord (
                row_index =int (idx ),
                order_id =order_id ,
                raw_patient_id =raw_pid ,
                canonical_patient_id =canon_pid ,
                numeric_id =num_id ,
                test_name =test_name ,
                ordered_at =ord_str ,
                collected_at =col_str ,
                resulted_at =res_str ,
                status =status ,
                raw_priority =raw_prio ,
                canonical_priority =canon_prio ,
                department =dept ,
                order_to_collect_minutes =round (order_to_col_min ,1 ),
                collect_to_result_minutes =round (col_to_res_min ,1 )if col_to_res_min is not None else None ,
                total_turnaround_minutes =round (total_tat_min ,1 )if total_tat_min is not None else None ,
                is_delayed =is_delayed ,
                delay_severity =delay_severity ,
                is_outpatient =is_outpatient 
            ))

        return records 

    @classmethod 
    def standardize_bed_data (cls ,df_bed :pd .DataFrame )->List [NormalizedBedRecord ]:
        """
        Standardizes manual Bed Occupancy logs / Bed census.
        Handles both individual bed logs and daily ward summaries.
        """
        records :List [NormalizedBedRecord ]=[]

        # Check if dataset is individual bed census (ward, bed_id, bed_status, patient_id, last_updated)
        if 'bed_status' in df_bed.columns or 'bed_id' in df_bed.columns:
            # Group or iterate by bed
            ward_counts = {}
            for _, r in df_bed.iterrows():
                w = cls.normalize_ward_name(str(r.get('ward', 'General Ward A')))
                if w not in ward_counts:
                    ward_counts[w] = {'total': 0, 'occupied': 0, 'available': 0, 'cleaning': 0, 'date': str(r.get('last_updated', datetime.now().strftime('%Y-%m-%d')))}
                ward_counts[w]['total'] += 1
                stat = str(r.get('bed_status', 'Available')).capitalize()
                if 'Occup' in stat:
                    ward_counts[w]['occupied'] += 1
                elif 'Clean' in stat:
                    ward_counts[w]['cleaning'] += 1
                else:
                    ward_counts[w]['available'] += 1
            
            for idx, (w, stats) in enumerate(ward_counts.items()):
                records.append(NormalizedBedRecord(
                    row_index = int(idx),
                    raw_date = stats['date'],
                    canonical_date = pd.to_datetime(stats['date'], errors='coerce').strftime('%Y-%m-%d') if pd.notnull(pd.to_datetime(stats['date'], errors='coerce')) else stats['date'][:10],
                    raw_ward = w,
                    canonical_ward = w,
                    total_beds = stats['total'],
                    occupied = stats['occupied'],
                    available = stats['available'],
                    raw_available = stats['available'],
                    was_available_imputed = False,
                    remarks = f"{stats['cleaning']} beds currently being cleaned",
                    has_daycare = False,
                    daycare_count = 0,
                    pending_discharge_count = 0,
                    is_system_downtime_approx = False
                ))
            return records

        for idx ,row in df_bed .iterrows ():
            raw_date =str (row.get ('Date', ''))
            dt_date =pd .to_datetime (raw_date ,format ="%d-%b-%y",errors ='coerce')
            canon_date =dt_date .strftime ("%Y-%m-%d")if pd .notnull (dt_date )else raw_date .strip ()

            raw_ward =str (row.get ('Ward', 'General Ward A'))
            canon_ward =cls .normalize_ward_name (raw_ward )

            total_beds =int (row.get ('Total Beds'))if pd .notnull (row.get ('Total Beds'))else WARD_CAPACITIES .get (canon_ward ,30 )
            occupied =int (row.get ('Occupied'))if pd .notnull (row.get ('Occupied'))else 0 

            raw_avail =float (row.get ('Available'))if pd .notnull (row.get ('Available'))else None 
            was_imputed =False 
            if raw_avail is None or np .isnan (raw_avail ):
                available =max (0 ,total_beds -occupied )
                was_imputed =True 
            else :
                available =int (raw_avail )

            raw_remarks =str (row.get ('Remarks', '')).strip ()if pd .notnull (row.get ('Remarks')) else None 
            remarks_lower =raw_remarks .lower ()if raw_remarks else ""

            has_daycare ="day-care"in remarks_lower or "daycare"in remarks_lower 
            daycare_count =1 if has_daycare else 0 

            pending_dis =0 
            if "discharges pending"in remarks_lower :
                match =re .search (r'(\d+)\s+discharges pending',remarks_lower )
                pending_dis =int (match .group (1 ))if match else 2 

            is_downtime ="system was down"in remarks_lower or "approx"in remarks_lower 

            records .append (NormalizedBedRecord (
                row_index =int (idx ),
                raw_date =raw_date ,
                canonical_date =canon_date ,
                raw_ward =raw_ward ,
                canonical_ward =canon_ward ,
                total_beds =total_beds ,
                occupied =occupied ,
                available =available ,
                raw_available =raw_avail ,
                was_available_imputed =was_imputed ,
                remarks =raw_remarks ,
                has_daycare =has_daycare ,
                daycare_count =daycare_count ,
                pending_discharge_count =pending_dis ,
                is_system_downtime_approx =is_downtime 
            ))

        return records 
