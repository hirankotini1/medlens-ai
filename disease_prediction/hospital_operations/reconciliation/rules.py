"""
Deterministic Reconciliation Rules Catalog for Hospital Operations
"""
from typing import List ,Dict 
from disease_prediction .hospital_operations .models import ReconciliationRuleDef 


RECONCILIATION_RULES :List [ReconciliationRuleDef ]=[
ReconciliationRuleDef (
rule_id ="RULE-REC-01",
rule_name ="Patient Identifier Normalization & Outpatient Classification",
category ="Patient Identity",
primary_source ="HIS Admissions & Discharges",
secondary_source ="Lab Order-to-Result",
description ="Patient IDs in HIS are prefixed (e.g. MCH-0001001) while Lab uses bare numeric IDs (e.g. 1023) or 7xxx series.",
rationale ="Lab orders with 7xxx series represent Outpatients/Walk-ins who receive diagnostic services without inpatient bed admission.",
action_taken ="Canonicalize all patient IDs to standard MCH-XXXXXXX format. Mark 7xxx series as Outpatient Diagnostic Services without dropping them."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-02",
rule_name ="HIS Duplicate Admission Record Resolution",
category ="Admissions & Census",
primary_source ="HIS Admissions & Discharges",
secondary_source =None ,
description ="Detects multiple identical admission rows for the same patient in the HIS extract (e.g., MCH-0001071, MCH-0001168).",
rationale ="Network/database re-transmission or double entry in HIS causes duplicate rows.",
action_taken ="Retain the initial verified admission record for active inpatient census calculation. Record secondary row in Conflict Register as DUPLICATE_HIS_RECORD with original indices preserved."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-03",
rule_name ="Manual Bed Sheet vs HIS Inpatient Census Reconciliation",
category ="Bed Management",
primary_source ="Manual Bed Occupancy Sheet",
secondary_source ="HIS Admissions & Discharges",
description ="Reconciles discrepancies between the manual nursing bed log and calculated HIS active patient occupancy for the same ward and date.",
rationale ="Manual bed counts frequently include day-care procedures, temporary hallway overflow, or pending discharge paperwork not yet updated in the HIS ledger.",
action_taken ="1) When Bed Remarks cite 'day-care patient', adjusted inpatient bed occupancy = Bed Occupied - Daycare count. 2) When Bed Remarks cite 'pending paperwork', physical occupancy is preserved from Bed Sheet while administrative status reflects HIS. 3) When Bed Remarks cite 'approx - system was down', HIS timestamped admissions are prioritized."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-04",
rule_name ="Missing Bed Sheet Entry Imputation & Auditing",
category ="Bed Management",
primary_source ="HIS Admissions & Discharges",
secondary_source ="Manual Bed Occupancy Sheet",
description ="Identifies days entirely missing from the manual bed occupancy sheet (July 9, 12, 19, 27, 31).",
rationale ="Nursing staff omitted manual logging on 5 dates during July 2026.",
action_taken ="Impute bed occupancy for missing dates using active HIS patient census filtered by ward capacity. Explicitly flag the record as IMPUTED_FROM_HIS_DUE_TO_MISSING_BED_SHEET in the audit trail."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-05",
rule_name ="Missing Available Bed Math Computation",
category ="Data Quality",
primary_source ="Manual Bed Occupancy Sheet",
secondary_source =None ,
description ="Handles blank/NaN entries in the 'Available' column of the manual bed sheet.",
rationale ="Nursing staff entered Total Beds and Occupied but omitted calculating Available beds.",
action_taken ="Compute Available Beds = max(0, Total Beds - Occupied) deterministically, tagging the field as CALCULATED_MISSING_FIELD."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-06",
rule_name ="Laboratory Turnaround & STAT Delay Classification",
category ="Laboratory Operations",
primary_source ="Lab Order-to-Result",
secondary_source =None ,
description ="Measures exact order-to-collection and collection-to-result durations across STAT, URGENT, and ROUTINE test tiers.",
rationale ="Highlights systemic diagnostic bottlenecks where critical emergency orders experience routine-level delays.",
action_taken ="Calculate durations from raw timestamps. Flag STAT orders exceeding 2 hours and URGENT orders exceeding 4 hours as Operational Delays."
),
ReconciliationRuleDef (
rule_id ="RULE-REC-07",
rule_name ="Canonical Ward Taxonomy Standardization",
category ="Facility & Taxonomy",
primary_source ="HIS & Bed Sources",
secondary_source =None ,
description ="Maps non-standard ward strings (e.g. 'I.C.U.', 'MICU ', 'Gen Ward A', 'Paediatrics ') to the hospital's 5 official wards.",
rationale ="Disparate spelling and trailing spaces cause fragmented reporting.",
action_taken ="Map all ward entities to canonical names: Intensive Care Unit (ICU), Medical ICU (MICU), General Ward A, General Ward B, Paediatrics."
)
]

def get_reconciliation_rules ()->List [ReconciliationRuleDef ]:
    return RECONCILIATION_RULES 

def get_rule_by_id (rule_id :str )->ReconciliationRuleDef :
    for rule in RECONCILIATION_RULES :
        if rule .rule_id ==rule_id :
            return rule 
    return RECONCILIATION_RULES [0 ]
