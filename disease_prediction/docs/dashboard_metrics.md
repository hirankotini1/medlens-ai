# MEDLENS Hospital Operations — Dashboard Metrics & Formula Reference

## 1. Active Inpatient Census
- **Formula**: Total unique verified admissions in HIS minus total recorded discharges as of snapshot date.
- **Value**: **56 active inpatients** (from 303 unique admissions and 249 completed discharges).

## 2. Bed Occupancy Percentage
- **Formula**: $\text{Hospital Occupancy} = \frac{\sum \text{Occupied Beds Across 5 Wards}}{\text{Total Hospital Licensed Capacity (98 Beds)}} \times 100$
- **Value**: **61.2%** (60 occupied beds, 38 available beds).
- **Ward Capacities**:
  - Intensive Care Unit (ICU): 12 beds
  - Medical ICU (MICU): 10 beds
  - General Ward A: 30 beds
  - General Ward B: 30 beds
  - Paediatrics: 16 beds

## 3. Laboratory Turnaround Time (TAT)
- **Order-to-Collection Duration**: $\text{collected\_at} - \text{ordered\_at}$ (Average: **95.0 minutes**).
- **Collection-to-Result Duration**: $\text{resulted\_at} - \text{collected\_at}$ (Average: **7.71 hours**).
- **Total Turnaround Time**: $\text{resulted\_at} - \text{ordered\_at}$ (Average: **9.30 hours**).
- **Priority Tier Breakdown**:
  - `STAT`: 9.39 hours average (Delayed beyond 2-hr target)
  - `URGENT`: 9.39 hours average
  - `ROUTINE`: 9.17 hours average

## 4. Transparent Data Quality Score Formula
- $\text{Score} = 100.0 - (\text{P}_{\text{dups}} + \text{P}_{\text{avail}} + \text{P}_{\text{days}} + \text{P}_{\text{conflicts}} + \text{P}_{\text{outpatient}})$
  - $\text{P}_{\text{dups}} = \min(5.0, 6 \times 0.5) = 3.0$
  - $\text{P}_{\text{avail}} = \min(5.0, 8 \times 0.3) = 2.4$
  - $\text{P}_{\text{days}} = \min(5.0, 5 \times 0.8) = 4.0$
  - $\text{P}_{\text{conflicts}} = \min(10.0, 25 \times 0.4) = 10.0$
  - $\text{P}_{\text{outpatient}} = \min(3.0, 34 \times 0.05) = 1.7$
- **Resulting Data Quality Score**: **78.9% (Good / Reliable)**.
