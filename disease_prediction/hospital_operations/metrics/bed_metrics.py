"""
Bed Capacity Metrics Calculator
"""
import pandas as pd 
from typing import List ,Dict ,Any 
from disease_prediction .hospital_operations .models import (
NormalizedBedRecord ,
NormalizedHISRecord ,
BedCapacityMetrics 
)
from disease_prediction .hospital_operations .normalization .standardizer import (
WARD_CAPACITIES ,
TOTAL_HOSPITAL_BEDS 
)


class BedCapacityMetricsCalculator :
    """
    Computes ward-level and hospital-wide bed occupancy, availability,
    capacity status, and longitudinal trends.
    """

    @staticmethod 
    def calculate_metrics (
    bed_records :List [NormalizedBedRecord ],
    his_records :List [NormalizedHISRecord ],
    warning_threshold :float =80.0 ,
    critical_threshold :float =90.0 
    )->BedCapacityMetrics :

        latest_date =max (r .canonical_date for r in bed_records )if bed_records else "2026-07-30"
        latest_bed_recs =[r for r in bed_records if r .canonical_date ==latest_date ]

        ward_breakdown =[]
        total_occ =0 
        total_avail =0 


        for ward_name ,capacity in WARD_CAPACITIES .items ():
            matching =[r for r in latest_bed_recs if r .canonical_ward ==ward_name ]
            if matching :
                occ =matching [0 ].occupied 
                avail =matching [0 ].available 
                rem =matching [0 ].remarks 
            else :

                day_start =f"{latest_date } 00:00:00"
                day_end =f"{latest_date } 23:59:59"
                his_active =[
                h for h in his_records 
                if not h .is_duplicate and h .canonical_ward ==ward_name 
                and h .admission_datetime <=day_end 
                and (h .discharge_datetime is None or h .discharge_datetime >=day_start )
                ]
                occ =len (his_active )
                avail =max (0 ,capacity -occ )
                rem ="Imputed from HIS"

            total_occ +=occ 
            total_avail +=avail 
            occ_pct =round ((occ /capacity *100 ),1 )if capacity >0 else 0.0 

            status ="Optimal"
            if occ_pct >=critical_threshold :
                status ="Critical"
            elif occ_pct >=warning_threshold :
                status ="Warning"

            ward_breakdown .append ({
            "ward_name":ward_name ,
            "total_beds":capacity ,
            "occupied_beds":occ ,
            "available_beds":avail ,
            "occupancy_percentage":occ_pct ,
            "status":status ,
            "remarks":rem 
            })

        overall_occ_pct =round ((total_occ /TOTAL_HOSPITAL_BEDS *100 ),1 )if TOTAL_HOSPITAL_BEDS >0 else 0.0 
        overall_status ="Optimal"
        if overall_occ_pct >=critical_threshold :
            overall_status ="Critical"
        elif overall_occ_pct >=warning_threshold :
            overall_status ="Warning"


        daily_trends =[]
        all_dates =sorted (list (set (r .canonical_date for r in bed_records )))

        for d in all_dates :
            day_recs =[r for r in bed_records if r .canonical_date ==d ]
            d_occ =sum (r .occupied for r in day_recs )
            d_avail =sum (r .available for r in day_recs )
            d_pct =round ((d_occ /TOTAL_HOSPITAL_BEDS *100 ),1 )
            daily_trends .append ({
            "date":d ,
            "occupied":d_occ ,
            "available":d_avail ,
            "total_capacity":TOTAL_HOSPITAL_BEDS ,
            "occupancy_percentage":d_pct 
            })

        return BedCapacityMetrics (
        total_hospital_beds =TOTAL_HOSPITAL_BEDS ,
        total_occupied_beds =total_occ ,
        total_available_beds =total_avail ,
        overall_occupancy_percentage =overall_occ_pct ,
        overall_status =overall_status ,
        ward_breakdown =ward_breakdown ,
        date_trend =daily_trends ,
        configured_warning_threshold =warning_threshold ,
        configured_critical_threshold =critical_threshold 
        )
