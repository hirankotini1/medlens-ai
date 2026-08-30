"""
Patient Flow & Census Metrics Calculator
"""
import pandas as pd 
from typing import List ,Dict ,Any 
from disease_prediction .hospital_operations .models import (
NormalizedHISRecord ,
PatientFlowMetrics 
)


class PatientFlowMetricsCalculator :
    """
    Computes patient admission, discharge, census, length of stay,
    and demographic distributions from normalized HIS records.
    """

    @staticmethod 
    def calculate_metrics (his_records :List [NormalizedHISRecord ])->PatientFlowMetrics :

        records =[r for r in his_records if not r .is_duplicate ]

        total_admissions =len (records )
        discharged_records =[r for r in records if not r .is_active and r .discharge_datetime is not None ]
        active_records =[r for r in records if r .is_active ]

        total_discharges =len (discharged_records )
        active_inpatients =len (active_records )


        los_days_list =[]
        for r in discharged_records :
            dt_adm =pd .to_datetime (r .admission_datetime )
            dt_dis =pd .to_datetime (r .discharge_datetime )
            los =(dt_dis -dt_adm ).total_seconds ()/86400.0 
            if los >=0 :
                los_days_list .append (los )

        alos =round (sum (los_days_list )/len (los_days_list ),1 )if los_days_list else 0.0 


        dept_dist :Dict [str ,int ]={}
        for r in records :
            dept_dist [r .admitting_department ]=dept_dist .get (r .admitting_department ,0 )+1 


        ward_dist :Dict [str ,int ]={}
        for r in active_records :
            ward_dist [r .canonical_ward ]=ward_dist .get (r .canonical_ward ,0 )+1 


        gender_dist :Dict [str ,int ]={}
        for r in records :
            gender_dist [r .canonical_gender ]=gender_dist .get (r .canonical_gender ,0 )+1 


        age_dist ={
        "0-17 (Pediatric)":0 ,
        "18-40 (Young Adult)":0 ,
        "41-65 (Middle Aged)":0 ,
        "65+ (Senior)":0 
        }
        for r in records :
            if r .age <18 :
                age_dist ["0-17 (Pediatric)"]+=1 
            elif r .age <=40 :
                age_dist ["18-40 (Young Adult)"]+=1 
            elif r .age <=65 :
                age_dist ["41-65 (Middle Aged)"]+=1 
            else :
                age_dist ["65+ (Senior)"]+=1 


        daily_map :Dict [str ,Dict [str ,int ]]={}
        for r in records :
            adm_date =r .admission_datetime .split ()[0 ]
            if adm_date .startswith ("2026-07")or adm_date .startswith ("2026-06"):
                daily_map .setdefault (adm_date ,{"date":adm_date ,"admissions":0 ,"discharges":0 })
                daily_map [adm_date ]["admissions"]+=1 

            if r .discharge_datetime :
                dis_date =r .discharge_datetime .split ()[0 ]
                if dis_date .startswith ("2026-07")or dis_date .startswith ("2026-06"):
                    daily_map .setdefault (dis_date ,{"date":dis_date ,"admissions":0 ,"discharges":0 })
                    daily_map [dis_date ]["discharges"]+=1 

        timeline =[daily_map [d ]for d in sorted (daily_map .keys ())]

        return PatientFlowMetrics (
        total_admissions =total_admissions ,
        total_discharges =total_discharges ,
        currently_active_inpatients =active_inpatients ,
        average_length_of_stay_days =alos ,
        department_distribution =dept_dist ,
        ward_distribution =ward_dist ,
        gender_distribution =gender_dist ,
        age_group_distribution =age_dist ,
        daily_admissions_discharges_timeline =timeline 
        )
