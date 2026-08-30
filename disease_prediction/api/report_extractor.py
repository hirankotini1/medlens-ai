"""
MEDLENS — Structured Laboratory Report Extractor & Normalizer
Separates patient/report metadata from clinical laboratory biomarkers,
normalizes parameter names, preserves source reference ranges, and computes extraction confidence.
"""

import re 
from typing import Dict ,Any ,List ,Optional ,Tuple 



EXCLUDED_METADATA_OR_HEADER_NAMES ={
"patient id","patient_id","patient no","patient number","pat id","uhid","mrn","pid","pat_id",
"patient name","patient_name","name of patient","patient","pt name","name",
"age","patient age","yrs","years","age / gender","age/sex","age/gender","age gender",
"gender","sex","biological sex","gender / sex","gender/sex",
"date of birth","dob","birth date",
"report id","report_id","report no","report number","accession","accession no","accession number","bill no","invoice no","test id",
"sample id","sample_id","sample no","sample number","specimen id","barcode","sid","specimen",
"report date","reported on","date of report","result date","released date","report_date","date",
"collection date","collected on","sample collection date","sample date","specimen date",
"referring doctor","referred by","doctor","consultant","ref by","prescribed by","physician","dr",
"laboratory name","lab name","diagnostic center","hospital","clinic","pathology laboratory",
"technician","lab technician","analyzed by","verified by",
"pathologist","doctor remarks","checked by","authorized by","consultant pathologist",
"phone","phone number","mobile","contact","email","address",
"test results","patient information","comments","disclaimer","method","signature","page",
"investigation","biomarker","parameter","test name","test","tests",
"observed value","result","results","value","observed","finding","findings",
"unit","units","reference interval","reference range","biological reference","biological reference interval","ref range","ref interval",
"status","flag","flags"
}


PLACEHOLDER_STRINGS ={
"-1","-999","-99","999","null","none","n/a","na","nil","not available",
"not reported","unknown","blank","","-","--","undefined","neg","pending"
}


CANONICAL_REF_RANGES :Dict [str ,Dict [str ,Any ]]={

"HGB":{"name":"Hemoglobin","unit":"g/dL","min":12.0 ,"max":16.0 ,"ref_str":"12.0 - 16.0","category":"cbc"},
"RBC":{"name":"RBC Count","unit":"million/µL","min":3.80 ,"max":5.20 ,"ref_str":"3.80 - 5.20","category":"cbc"},
"PCV":{"name":"PCV / Hematocrit","unit":"%","min":36.0 ,"max":46.0 ,"ref_str":"36.0 - 46.0","category":"cbc"},
"MCV":{"name":"MCV","unit":"fL","min":80.0 ,"max":100.0 ,"ref_str":"80.0 - 100.0","category":"cbc"},
"MCH":{"name":"MCH","unit":"pg","min":27.0 ,"max":32.0 ,"ref_str":"27.0 - 32.0","category":"cbc"},
"MCHC":{"name":"MCHC","unit":"g/dL","min":31.5 ,"max":34.5 ,"ref_str":"31.5 - 34.5","category":"cbc"},
"RDW":{"name":"RDW","unit":"%","min":11.5 ,"max":14.5 ,"ref_str":"11.5 - 14.5","category":"cbc"},
"WBC":{"name":"WBC Count","unit":"/µL","min":4000 ,"max":11000 ,"ref_str":"4000 - 11000","category":"cbc"},
"PLT":{"name":"Platelet Count","unit":"/µL","min":150000 ,"max":450000 ,"ref_str":"150000 - 450000","category":"cbc"},
"FERRITIN":{"name":"Ferritin","unit":"ng/mL","min":15.0 ,"max":200.0 ,"ref_str":"15.0 - 200.0","category":"cbc"},
"ESR":{"name":"ESR","unit":"mm/hr","min":0.0 ,"max":20.0 ,"ref_str":"0.0 - 20.0","category":"cbc"},
"NEUTROPHILS":{"name":"Neutrophils","unit":"%","min":40.0 ,"max":75.0 ,"ref_str":"40.0 - 75.0","category":"cbc"},
"LYMPHOCYTES":{"name":"Lymphocytes","unit":"%","min":20.0 ,"max":45.0 ,"ref_str":"20.0 - 45.0","category":"cbc"},
"EOSINOPHILS":{"name":"Eosinophils","unit":"%","min":1.0 ,"max":6.0 ,"ref_str":"1.0 - 6.0","category":"cbc"},
"MONOCYTES":{"name":"Monocytes","unit":"%","min":2.0 ,"max":10.0 ,"ref_str":"2.0 - 10.0","category":"cbc"},
"BASOPHILS":{"name":"Basophils","unit":"%","min":0.0 ,"max":2.0 ,"ref_str":"0.0 - 2.0","category":"cbc"},
"DIFFERENTIAL_COUNT":{"name":"Differential Count","unit":"%","min":98.0 ,"max":100.0 ,"ref_str":"100%","category":"cbc"},
"PDW":{"name":"Platelet Distribution Width","unit":"%","min":9.0 ,"max":17.0 ,"ref_str":"9.0 - 17.0","category":"cbc"},
"platelet_distribution_width":{"name":"Platelet Distribution Width","unit":"%","min":9.0 ,"max":17.0 ,"ref_str":"9.0 - 17.0","category":"cbc"},


"TOTAL_BILIRUBIN":{"name":"Total Bilirubin","unit":"mg/dL","min":0.2 ,"max":1.2 ,"ref_str":"0.2 - 1.2","category":"lft"},
"DIRECT_BILIRUBIN":{"name":"Direct Bilirubin","unit":"mg/dL","min":0.0 ,"max":0.3 ,"ref_str":"0.0 - 0.3","category":"lft"},
"INDIRECT_BILIRUBIN":{"name":"Indirect Bilirubin","unit":"mg/dL","min":0.2 ,"max":0.8 ,"ref_str":"0.2 - 0.8","category":"lft"},
"ALP":{"name":"ALP","unit":"U/L","min":44 ,"max":147 ,"ref_str":"44 - 147","category":"lft"},
"ALT":{"name":"ALT","unit":"U/L","min":10 ,"max":40 ,"ref_str":"10 - 40","category":"lft"},
"AST":{"name":"AST","unit":"U/L","min":10 ,"max":40 ,"ref_str":"10 - 40","category":"lft"},
"TOTAL_PROTEIN":{"name":"Total Protein","unit":"g/dL","min":6.0 ,"max":8.3 ,"ref_str":"6.0 - 8.3","category":"lft"},
"ALBUMIN":{"name":"Albumin","unit":"g/dL","min":3.5 ,"max":5.0 ,"ref_str":"3.5 - 5.0","category":"lft"},
"GLOBULIN":{"name":"Globulin","unit":"g/dL","min":2.0 ,"max":3.5 ,"ref_str":"2.0 - 3.5","category":"lft"},
"AG_RATIO":{"name":"A/G Ratio","unit":"ratio","min":1.0 ,"max":2.2 ,"ref_str":"1.0 - 2.2","category":"lft"},


"TSH":{"name":"TSH","unit":"µIU/mL","min":0.40 ,"max":4.20 ,"ref_str":"0.40 - 4.20","category":"thyroid"},
"T4":{"name":"T4","unit":"µg/dL","min":4.5 ,"max":12.0 ,"ref_str":"4.5 - 12.0","category":"thyroid"},
"T3":{"name":"T3","unit":"ng/dL","min":0.8 ,"max":2.0 ,"ref_str":"0.8 - 2.0","category":"thyroid"},
"FREE_T3":{"name":"Free T3","unit":"pg/mL","min":2.0 ,"max":4.4 ,"ref_str":"2.0 - 4.4","category":"thyroid"},
"FREE_T4":{"name":"Free T4","unit":"ng/dL","min":0.8 ,"max":1.8 ,"ref_str":"0.8 - 1.8","category":"thyroid"},
"TSH_RESPONSE":{"name":"TSH Response","unit":"ratio","min":1.0 ,"max":5.0 ,"ref_str":"1.0 - 5.0","category":"thyroid"},
"T3_RESIN_UPTAKE":{"name":"T3 Resin Uptake","unit":"%","min":24.0 ,"max":39.0 ,"ref_str":"24.0 - 39.0","category":"thyroid"},


"GLUCOSE":{"name":"Glucose (Fasting)","unit":"mg/dL","min":70.0 ,"max":100.0 ,"ref_str":"70.0 - 100.0","category":"general"},
"HBA1C":{"name":"HbA1c","unit":"%","min":4.0 ,"max":5.6 ,"ref_str":"4.0 - 5.6","category":"general"},
"CREATININE":{"name":"Creatinine","unit":"mg/dL","min":0.6 ,"max":1.2 ,"ref_str":"0.6 - 1.2","category":"general"},
"UREA":{"name":"Urea / BUN","unit":"mg/dL","min":7.0 ,"max":20.0 ,"ref_str":"7.0 - 20.0","category":"general"},
"CRP":{"name":"CRP","unit":"mg/L","min":0.0 ,"max":5.0 ,"ref_str":"0.0 - 5.0","category":"general"},
"SODIUM":{"name":"Sodium","unit":"mmol/L","min":135.0 ,"max":145.0 ,"ref_str":"135.0 - 145.0","category":"general"},
"POTASSIUM":{"name":"Potassium","unit":"mmol/L","min":3.5 ,"max":5.0 ,"ref_str":"3.5 - 5.0","category":"general"},
"CALCIUM":{"name":"Calcium","unit":"mg/dL","min":8.5 ,"max":10.5 ,"ref_str":"8.5 - 10.5","category":"general"},
"VITAMIN_B12":{"name":"Vitamin B12","unit":"pg/mL","min":200.0 ,"max":900.0 ,"ref_str":"200.0 - 900.0","category":"general"},
"VITAMIN_D":{"name":"Vitamin D (25-OH)","unit":"ng/mL","min":30.0 ,"max":100.0 ,"ref_str":"30.0 - 100.0","category":"general"},


"CERULOPLASMIN":{"name":"Ceruloplasmin","unit":"mg/dL","min":20.0 ,"max":40.0 ,"ref_str":"20.0 - 40.0","category":"specialized"},
"URINARY_COPPER_24H":{"name":"24-Hour Urinary Copper","unit":"µg/24h","min":10.0 ,"max":60.0 ,"ref_str":"10.0 - 60.0","category":"specialized"},
"SERUM_COPPER":{"name":"Serum Copper","unit":"µg/dL","min":70.0 ,"max":140.0 ,"ref_str":"70.0 - 140.0","category":"specialized"},


"LDH":{"name":"LDH","unit":"U/L","min":140.0 ,"max":280.0 ,"ref_str":"140.0 - 280.0","category":"specialized"},
"HAPTOGLOBIN":{"name":"Haptoglobin","unit":"mg/dL","min":30.0 ,"max":200.0 ,"ref_str":"30.0 - 200.0","category":"specialized"},
"RETICULOCYTES":{"name":"Reticulocyte Count","unit":"%","min":0.5 ,"max":2.5 ,"ref_str":"0.5 - 2.5","category":"cbc"},
"G6PD":{"name":"G6PD Enzyme Activity","unit":"U/g Hb","min":7.0 ,"max":20.5 ,"ref_str":"7.0 - 20.5","category":"specialized"},
"G6PD_ENZYME_ACTIVITY":{"name":"G6PD Enzyme Activity","unit":"U/g Hb","min":7.0 ,"max":20.5 ,"ref_str":"7.0 - 20.5","category":"specialized"},
"ALPHA1_ANTITRYPSIN":{"name":"Alpha-1 Antitrypsin","unit":"mg/dL","min":90.0 ,"max":200.0 ,"ref_str":"90.0 - 200.0","category":"specialized"},
"PORPHOBILINOGEN":{"name":"Urinary Porphobilinogen (PBG)","unit":"mg/24h","min":0.0 ,"max":2.0 ,"ref_str":"0.0 - 2.0","category":"specialized"},
"IGG":{"name":"Immunoglobulin G (IgG)","unit":"mg/dL","min":700.0 ,"max":1600.0 ,"ref_str":"700.0 - 1600.0","category":"specialized"},
"IGM":{"name":"Immunoglobulin M (IgM)","unit":"mg/dL","min":40.0 ,"max":230.0 ,"ref_str":"40.0 - 230.0","category":"specialized"},
"ADAMTS13":{"name":"ADAMTS13 Activity","unit":"%","min":68.0 ,"max":160.0 ,"ref_str":"68.0 - 160.0","category":"specialized"},
"M_SPIKE":{"name":"Monoclonal M-Spike","unit":"g/dL","min":0.0 ,"max":0.0 ,"ref_str":"Negative","category":"specialized"},
"CORTISOL":{"name":"Serum Cortisol (Morning)","unit":"µg/dL","min":5.0 ,"max":25.0 ,"ref_str":"5.0 - 25.0","category":"specialized"},
"IRON":{"name":"Serum Iron","unit":"µg/dL","min":60.0 ,"max":170.0 ,"ref_str":"60.0 - 170.0","category":"cbc"},
"TIBC":{"name":"TIBC","unit":"µg/dL","min":250.0 ,"max":450.0 ,"ref_str":"250.0 - 450.0","category":"cbc"},
"TRANSFERRIN_SAT":{"name":"Transferrin Saturation","unit":"%","min":20.0 ,"max":50.0 ,"ref_str":"20.0 - 50.0","category":"cbc"}
}


PARAMETER_ALIASES :Dict [str ,str ]={

"hemoglobin":"HGB","haemoglobin":"HGB","hgb":"HGB","hb":"HGB","hemoglobin conc":"HGB","s hemoglobin":"HGB","serum hemoglobin":"HGB","total hemoglobin":"HGB","hemoglobin_g_dl":"HGB",
"total rbc count":"RBC","total rbc":"RBC","rbc count":"RBC","red blood cell count":"RBC","red blood cells":"RBC","red blood cell":"RBC","rbc":"RBC","erythrocytes":"RBC","total erythrocytes":"RBC",
"pcv / hematocrit":"PCV","pcv/hematocrit":"PCV","pcv":"PCV","packed cell volume":"PCV","packed cell volume pcv":"PCV","hematocrit":"PCV","hct":"PCV",
"mean corpuscular volume":"MCV","mean corpuscular vol":"MCV","mcv":"MCV",
"mean corpuscular hemoglobin":"MCH","mean corpuscular haemoglobin":"MCH","mean corpuscular hgb":"MCH","mch":"MCH",
"mean corpuscular hemoglobin concentration":"MCHC","mean corpuscular haemoglobin concentration":"MCHC","mean corpuscular hgb concentration":"MCHC","mchc":"MCHC",
"red cell distribution width":"RDW","red cell dist width":"RDW","rdw":"RDW","rdw cv":"RDW","rdw sd":"RDW","rdw-cv":"RDW","rdw-sd":"RDW",
"total leukocyte count":"WBC","total leucocyte count":"WBC","total leukocyte count wbc":"WBC","total leucocyte count wbc":"WBC","total leukocyte":"WBC","tlc":"WBC","wbc count":"WBC","wbc":"WBC","white blood cells":"WBC","white blood cell count":"WBC","white blood cell":"WBC","leukocytes":"WBC","total wbc":"WBC","wbc_count":"WBC",
"platelet count":"PLT","platelets":"PLT","plt count":"PLT","plt":"PLT","thrombocytes":"PLT","total platelets":"PLT","plt mm3":"PLT","plt /mm3":"PLT","plt_mm3":"PLT","platelet_count":"PLT",
"serum ferritin":"FERRITIN","ferritin":"FERRITIN","s ferritin":"FERRITIN",
"erythrocyte sedimentation rate":"ESR","esr":"ESR",
"neutrophils":"NEUTROPHILS","lymphocytes":"LYMPHOCYTES","eosinophils":"EOSINOPHILS","monocytes":"MONOCYTES","basophils":"BASOPHILS",
"differential count":"DIFFERENTIAL_COUNT","differential leucocyte count":"DIFFERENTIAL_COUNT","differential leukocyte count":"DIFFERENTIAL_COUNT","dlc":"DIFFERENTIAL_COUNT","differential_count":"DIFFERENTIAL_COUNT",
"platelet distribution width":"PDW","platelet dist width":"PDW","pdw":"PDW","platelet_distribution_width":"PDW",
"reticulocyte count":"RETICULOCYTES","reticulocytes":"RETICULOCYTES","retic count":"RETICULOCYTES",


"total bilirubin":"TOTAL_BILIRUBIN","bilirubin total":"TOTAL_BILIRUBIN","t bili":"TOTAL_BILIRUBIN","s bilirubin total":"TOTAL_BILIRUBIN","serum bilirubin total":"TOTAL_BILIRUBIN","serum bilirubin":"TOTAL_BILIRUBIN","bilirubin":"TOTAL_BILIRUBIN",
"direct bilirubin":"DIRECT_BILIRUBIN","conjugated bilirubin":"DIRECT_BILIRUBIN","d bili":"DIRECT_BILIRUBIN","s bilirubin direct":"DIRECT_BILIRUBIN","serum bilirubin direct":"DIRECT_BILIRUBIN",
"indirect bilirubin":"INDIRECT_BILIRUBIN","unconjugated bilirubin":"INDIRECT_BILIRUBIN","i bili":"INDIRECT_BILIRUBIN","s bilirubin indirect":"INDIRECT_BILIRUBIN","serum bilirubin indirect":"INDIRECT_BILIRUBIN",
"alkaline phosphatase":"ALP","alkaline phosphatase alp":"ALP","alkaline phosphotase":"ALP","alp":"ALP","s alp":"ALP","serum alp":"ALP","serum alkaline phosphatase":"ALP",
"alt / sgpt":"ALT","alt/sgpt":"ALT","alanine aminotransferase":"ALT","alamine aminotransferase":"ALT","alt":"ALT","sgpt":"ALT","alt sgpt":"ALT","s alt":"ALT","serum alt":"ALT","serum sgpt":"ALT",
"ast / sgot":"AST","ast/sgot":"AST","aspartate aminotransferase":"AST","ast":"AST","sgot":"AST","ast sgot":"AST","s ast":"AST","serum ast":"AST","serum sgot":"AST",
"total protein":"TOTAL_PROTEIN","total proteins":"TOTAL_PROTEIN","total protiens":"TOTAL_PROTEIN","s protein":"TOTAL_PROTEIN","serum protein":"TOTAL_PROTEIN","total serum protein":"TOTAL_PROTEIN",
"serum albumin":"ALBUMIN","albumin":"ALBUMIN","s albumin":"ALBUMIN","albumin serum":"ALBUMIN",
"globulin":"GLOBULIN","serum globulin":"GLOBULIN","s globulin":"GLOBULIN",
"a/g ratio":"AG_RATIO","ag ratio":"AG_RATIO","a g ratio":"AG_RATIO","albumin and globulin ratio":"AG_RATIO","albumin globulin ratio":"AG_RATIO","albumin/globulin ratio":"AG_RATIO","ag_ratio":"AG_RATIO",


"thyroid stimulating hormone":"TSH","tsh":"TSH","s tsh":"TSH","ultra tsh":"TSH","serum tsh":"TSH",
"total triiodothyronine":"T3","triiodothyronine":"T3","total t3":"T3","t3":"T3","s t3":"T3","serum t3":"T3",
"total thyroxine":"T4","thyroxine":"T4","total t4":"T4","t4":"T4","s t4":"T4","serum t4":"T4",
"free t3":"FREE_T3","ft3":"FREE_T3","free triiodothyronine":"FREE_T3",
"free t4":"FREE_T4","ft4":"FREE_T4","free thyroxine":"FREE_T4",
"tsh response":"TSH_RESPONSE","tsh response to trh":"TSH_RESPONSE","tsh response trh":"TSH_RESPONSE",
"t3 resin uptake":"T3_RESIN_UPTAKE","t3 uptake":"T3_RESIN_UPTAKE","t3 resin":"T3_RESIN_UPTAKE","t3 resin uptake %":"T3_RESIN_UPTAKE",


"ceruloplasmin":"CERULOPLASMIN","serum ceruloplasmin":"CERULOPLASMIN","s ceruloplasmin":"CERULOPLASMIN","cp":"CERULOPLASMIN",
"24-hour urinary copper":"URINARY_COPPER_24H","24-hr urinary copper":"URINARY_COPPER_24H","24 hour urinary copper":"URINARY_COPPER_24H","24 hour urine copper":"URINARY_COPPER_24H","urinary copper":"URINARY_COPPER_24H","urine copper 24h":"URINARY_COPPER_24H","urine copper":"URINARY_COPPER_24H","24-hour urine copper":"URINARY_COPPER_24H",
"serum copper":"SERUM_COPPER","total copper":"SERUM_COPPER","copper serum":"SERUM_COPPER","s copper":"SERUM_COPPER","copper":"SERUM_COPPER",


"alpha-1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha 1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha-1-antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha 1-antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha1-antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha1antitrypsin":"ALPHA1_ANTITRYPSIN",
"serum alpha-1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"serum alpha 1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"s alpha-1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"s alpha 1 antitrypsin":"ALPHA1_ANTITRYPSIN",
"alpha-1 antitrypsin aat":"ALPHA1_ANTITRYPSIN",
"alpha 1 antitrypsin aat":"ALPHA1_ANTITRYPSIN",
"alpha-1 antitrypsin (aat)":"ALPHA1_ANTITRYPSIN",
"alpha 1 antitrypsin (aat)":"ALPHA1_ANTITRYPSIN",
"alpha-1 proteinase inhibitor":"ALPHA1_ANTITRYPSIN",
"alpha 1 proteinase inhibitor":"ALPHA1_ANTITRYPSIN",
"alpha-1-proteinase inhibitor":"ALPHA1_ANTITRYPSIN",
"alpha-1 protease inhibitor":"ALPHA1_ANTITRYPSIN",
"alpha 1 protease inhibitor":"ALPHA1_ANTITRYPSIN",
"alpha1 proteinase inhibitor":"ALPHA1_ANTITRYPSIN",
"serum aat":"ALPHA1_ANTITRYPSIN",
"s aat":"ALPHA1_ANTITRYPSIN",
"aat":"ALPHA1_ANTITRYPSIN",


"g6pd enzyme activity":"G6PD_ENZYME_ACTIVITY","g6pd activity":"G6PD_ENZYME_ACTIVITY","g6pd":"G6PD_ENZYME_ACTIVITY","g6pd enzyme":"G6PD_ENZYME_ACTIVITY",
"glucose-6-phosphate dehydrogenase activity":"G6PD_ENZYME_ACTIVITY","glucose 6 phosphate dehydrogenase activity":"G6PD_ENZYME_ACTIVITY",
"glucose-6-phosphate dehydrogenase":"G6PD_ENZYME_ACTIVITY","glucose 6 phosphate dehydrogenase":"G6PD_ENZYME_ACTIVITY",
"g 6 pd":"G6PD_ENZYME_ACTIVITY","g-6-pd":"G6PD_ENZYME_ACTIVITY","g6pd quantitative":"G6PD_ENZYME_ACTIVITY","quantitative g6pd":"G6PD_ENZYME_ACTIVITY","g6pd assay":"G6PD_ENZYME_ACTIVITY","erythrocyte g6pd":"G6PD_ENZYME_ACTIVITY",
"urinary porphobilinogen":"PORPHOBILINOGEN","porphobilinogen":"PORPHOBILINOGEN","urine pbg":"PORPHOBILINOGEN","urinary pbg":"PORPHOBILINOGEN","pbg":"PORPHOBILINOGEN","porphyrins":"PORPHOBILINOGEN","delta ala":"PORPHOBILINOGEN",
"immunoglobulin g":"IGG","serum igg":"IGG","igg":"IGG","s igg":"IGG","igg total":"IGG",
"immunoglobulin m":"IGM","serum igm":"IGM","igm":"IGM","s igm":"IGM","igm total":"IGM",
"adamts13 activity":"ADAMTS13","adamts13":"ADAMTS13","adamts 13":"ADAMTS13","adamts-13":"ADAMTS13",
"monoclonal m spike":"M_SPIKE","m spike":"M_SPIKE","m-spike":"M_SPIKE","monoclonal band":"M_SPIKE","paraprotein":"M_SPIKE","m protein":"M_SPIKE","m band":"M_SPIKE",
"serum cortisol":"CORTISOL","cortisol":"CORTISOL","morning cortisol":"CORTISOL","8 am cortisol":"CORTISOL","s cortisol":"CORTISOL",


"lactate dehydrogenase":"LDH","lactic dehydrogenase":"LDH","ldh":"LDH","s ldh":"LDH","serum ldh":"LDH",
"haptoglobin":"HAPTOGLOBIN","serum haptoglobin":"HAPTOGLOBIN","s haptoglobin":"HAPTOGLOBIN",
"serum iron":"IRON","iron":"IRON","s iron":"IRON",
"total iron binding capacity":"TIBC","tibc":"TIBC",
"transferrin saturation":"TRANSFERRIN_SAT","iron saturation":"TRANSFERRIN_SAT","tsat":"TRANSFERRIN_SAT",


"fasting blood glucose":"GLUCOSE","fasting glucose":"GLUCOSE","glucose":"GLUCOSE","fbs":"GLUCOSE","blood sugar fasting":"GLUCOSE",
"glycated hemoglobin":"HBA1C","hba1c":"HBA1C","glycosylated hemoglobin":"HBA1C",
"serum creatinine":"CREATININE","creatinine":"CREATININE","s creatinine":"CREATININE",
"blood urea nitrogen":"UREA","blood urea":"UREA","urea":"UREA","bun":"UREA",
"c reactive protein":"CRP","crp":"CRP","c-reactive protein":"CRP","s crp":"CRP","serum crp":"CRP",
"sodium":"SODIUM","potassium":"POTASSIUM","calcium":"CALCIUM",
"vitamin b12":"VITAMIN_B12","vitamin d":"VITAMIN_D","vitamin d 25 oh":"VITAMIN_D"
}



CRITICAL_PANIC_THRESHOLDS :Dict [str ,Dict [str ,Optional [float ]]]={
"HGB":{"critical_low":6.0 ,"critical_high":20.0 },
"PLT":{"critical_low":20000.0 ,"critical_high":1000000.0 },
"platelet_count":{"critical_low":20000.0 ,"critical_high":1000000.0 },
"WBC":{"critical_low":1500.0 ,"critical_high":30000.0 },
"wbc_count":{"critical_low":1500.0 ,"critical_high":30000.0 },
"POTASSIUM":{"critical_low":2.8 ,"critical_high":6.2 },
"SODIUM":{"critical_low":120.0 ,"critical_high":160.0 },
"CALCIUM":{"critical_low":6.5 ,"critical_high":13.0 },
"GLUCOSE":{"critical_low":45.0 ,"critical_high":450.0 },
"TOTAL_BILIRUBIN":{"critical_low":None ,"critical_high":15.0 },
"FERRITIN":{"critical_low":5.0 ,"critical_high":None }
}


def is_metadata_or_header_field (name :str )->bool :
    """Checks if a string corresponds to report/patient metadata or table header rows."""
    if not name :
        return True 
    clean =re .sub (r'[^a-zA-Z0-9\s]',' ',name .lower ())
    clean =re .sub (r'\s+',' ',clean ).strip ()
    return clean in EXCLUDED_METADATA_OR_HEADER_NAMES or any (clean ==ex for ex in EXCLUDED_METADATA_OR_HEADER_NAMES )


def is_placeholder_value (val :Any )->bool :
    """Checks whether a value is a placeholder or invalid representation."""
    if val is None :
        return True 
    s =str (val ).strip ().lower ()
    return s in PLACEHOLDER_STRINGS 


def parse_numeric_value (val_str :Any )->Optional [float ]:
    """Extracts valid float number from string, handling commas and units."""
    if val_str is None or is_placeholder_value (val_str ):
        return None 
    if isinstance (val_str ,(int ,float )):
        return float (val_str )

    s =str (val_str ).replace (",","").strip ()
    match =re .search (r'[-+]?\d*\.?\d+',s )
    if match :
        try :
            return float (match .group (0 ))
        except ValueError :
            return None 
    return None 


def parse_source_reference_range (ref_str :str )->Tuple [Optional [float ],Optional [float ]]:
    """Parses min and max range limits from string expressions like '12.0 - 16.0', '24–39%', or '< 200'."""
    if not ref_str :
        return None ,None 

    clean =ref_str .replace ('%','').strip ()
    m_range =re .search (r'([-+]?\d*\.?\d+)\s*(?:-|to|–|—)\s*([-+]?\d*\.?\d+)',clean )
    if m_range :
        try :
            return float (m_range .group (1 )),float (m_range .group (2 ))
        except ValueError :
            pass 


    m_single =re .match (r'^\s*([-+]?\d*\.?\d+)\s*$',clean )
    if m_single :
        try :
            val =float (m_single .group (1 ))
            return val *0.95 ,val *1.05 
        except ValueError :
            pass 

    m_less =re .search (r'<\s*([-+]?\d*\.?\d+)',clean )
    if m_less :
        try :
            return 0.0 ,float (m_less .group (1 ))
        except ValueError :
            pass 

    m_greater =re .search (r'>\s*([-+]?\d*\.?\d+)',clean )
    if m_greater :
        try :
            return float (m_greater .group (1 )),float ('inf')
        except ValueError :
            pass 

    return None ,None 



def calculate_biomarker_status (
val :float ,
ref_str :str ,
canonical_key :Optional [str ]=None ,
src_status :str =""
)->str :
    """
    Calculates physiological status: LOW, NORMAL, HIGH.
    Only applies CRITICAL thresholds when explicit panic limits are crossed.
    """

    if canonical_key and canonical_key in CRITICAL_PANIC_THRESHOLDS :
        panic =CRITICAL_PANIC_THRESHOLDS [canonical_key ]
        crit_low =panic .get ("critical_low")
        crit_high =panic .get ("critical_high")

        norm_val =val 
        if canonical_key in ["PLT","platelet_count"]and val <1000 :
            norm_val =val *1000.0 
        elif canonical_key in ["WBC","wbc_count"]and val <100 :
            norm_val =val *1000.0 

        if crit_low is not None and norm_val <crit_low :
            return "CRITICAL LOW"
        if crit_high is not None and norm_val >crit_high :
            return "CRITICAL HIGH"


    min_v ,max_v =parse_source_reference_range (ref_str )
    if min_v is None or max_v is None :
        if canonical_key and canonical_key in CANONICAL_REF_RANGES :
            min_v =CANONICAL_REF_RANGES [canonical_key ]["min"]
            max_v =CANONICAL_REF_RANGES [canonical_key ]["max"]

    if min_v is not None and max_v is not None :
        norm_val =val 

        if canonical_key in ["PLT","platelet_count"]and val >1000 and max_v <1000 :
            norm_val =val /1000.0 
        elif canonical_key in ["PLT","platelet_count"]and val <1000 and max_v >10000 :
            norm_val =val *1000.0 

        if norm_val <min_v :
            return "LOW"
        elif norm_val >max_v :
            return "HIGH"
        return "NORMAL"


    if src_status :
        s_upper =src_status .upper ()
        if "CRIT"in s_upper :return "CRITICAL"
        if "LOW"in s_upper :return "LOW"
        if "HIGH"in s_upper or "ABN"in s_upper :return "HIGH"
        if "NORM"in s_upper :return "NORMAL"

    return "NORMAL"


def normalize_param_name (raw_name :str )->Tuple [Optional [str ],Optional [Dict [str ,Any ]]]:
    """Maps raw parameter name to canonical biomarker key and metadata."""
    if not raw_name or is_metadata_or_header_field (raw_name ):
        return None ,None 

    clean_name =re .sub (r'[^a-zA-Z0-9\s]',' ',raw_name .lower ())
    clean_name =re .sub (r'\s+',' ',clean_name ).strip ()

    canonical_key =PARAMETER_ALIASES .get (clean_name )


    if not canonical_key :
        sorted_aliases =sorted (PARAMETER_ALIASES .keys (),key =len ,reverse =True )
        for alias in sorted_aliases :
            pattern =rf'(?i)(?:^|\s){re .escape (alias )}(?:$|\s)'
            if re .search (pattern ,clean_name ):
                canonical_key =PARAMETER_ALIASES [alias ]
                break 

    if canonical_key and canonical_key in CANONICAL_REF_RANGES :
        return canonical_key ,CANONICAL_REF_RANGES [canonical_key ]

    return canonical_key ,None 


def extract_metadata_from_lines (lines :List [str ])->Dict [str ,Any ]:
    """Extracts patient and report metadata fields from document header lines."""
    meta :Dict [str ,Any ]={
    "patient_id":"",
    "patient_name":"",
    "age":None ,
    "gender":"",
    "report_id":"",
    "report_date":"",
    "sample_id":"",
    "referring_doctor":"",
    "lab_name":""
    }

    for line in lines :
        parts =re .split (r'\t+|\s{3,}',line .strip ())
        for part in parts :
            p_clean =part .strip ()
            if not p_clean :
                continue 


            m =re .search (r'(?i)\b(?:patient\s*id|pat\s*id|uhid|mrn|pid)\s*[:=\t\s]+([A-Za-z0-9\-_]+)',p_clean )
            if m and not meta ["patient_id"]:
                meta ["patient_id"]=m .group (1 ).strip ()


            m =re .search (r'(?i)\b(?:report\s*id|report\s*no|accession\s*no|bill\s*no)\s*[:=\t\s]+([A-Za-z0-9\-_]+)',p_clean )
            if m and not meta ["report_id"]:
                meta ["report_id"]=m .group (1 ).strip ()


            m =re .search (r'(?i)\b(?:patient\s*name|name\s*of\s*patient|pt\s*name|name)\s*[:=\t\s]+([A-Za-z\s\.\-_]+)',p_clean )
            if m and not meta ["patient_name"]:
                cand_name =m .group (1 ).strip ()
                if not is_metadata_or_header_field (cand_name )and len (cand_name )>1 :
                    meta ["patient_name"]=cand_name 


            m_comb =re .search (r'(?i)(?:age\s*[/,;&|]\s*(?:gender|sex)|demographics)?\s*[:=\t\s]*\b(\d{1,3})\s*(?:yrs?|years?|y|yo)?\s*[/,;&|\s]+\s*(male|female|other|m|f)\b',p_clean )
            if m_comb :
                if meta ["age"]is None :
                    try :
                        meta ["age"]=int (m_comb .group (1 ))
                    except ValueError :
                        pass 
                if not meta ["gender"]:
                    g =m_comb .group (2 ).strip ().capitalize ()
                    meta ["gender"]="Female"if g in ["F","Female"]else ("Male"if g in ["M","Male"]else g )


            m_comb_rev =re .search (r'(?i)(?:(?:gender|sex)\s*[/,;&|]\s*age)?\s*[:=\t\s]*\b(male|female|other|m|f)\b\s*[/,;&|\s]+\s*(\d{1,3})\s*(?:yrs?|years?|y|yo)?\b',p_clean )
            if m_comb_rev :
                if not meta ["gender"]:
                    g =m_comb_rev .group (1 ).strip ().capitalize ()
                    meta ["gender"]="Female"if g in ["F","Female"]else ("Male"if g in ["M","Male"]else g )
                if meta ["age"]is None :
                    try :
                        meta ["age"]=int (m_comb_rev .group (2 ))
                    except ValueError :
                        pass 


            if meta ["age"]is None :
                m =re .search (r'(?i)\b(?:age)\s*[:=\t\s]+(\d+)\s*(?:yrs|years|y)?',p_clean )
                if m :
                    try :
                        meta ["age"]=int (m .group (1 ))
                    except ValueError :
                        pass 


            if not meta ["gender"]:
                m =re .search (r'(?i)\b(?:gender|sex)\s*[:=\t\s]+(Female|Male|Other|F|M)\b',p_clean )
                if m :
                    g =m .group (1 ).strip ().capitalize ()
                    meta ["gender"]="Female"if g in ["F","Female"]else ("Male"if g in ["M","Male"]else g )


            m =re .search (r'(?i)\b(?:date|report\s*date|reported\s*on)\s*[:=\t\s]+([0-9]{1,2}[-/\.][A-Za-z0-9]{2,4}[-/\.][0-9]{2,4}|[A-Za-z0-9\s,]{8,20})',p_clean )
            if m and not meta ["report_date"]:
                meta ["report_date"]=m .group (1 ).strip ()


            m =re .search (r'(?i)\b(?:sample\s*id|sample\s*no|specimen\s*id)\s*[:=\t\s]+([A-Za-z0-9\-_]+)',p_clean )
            if m and not meta ["sample_id"]:
                meta ["sample_id"]=m .group (1 ).strip ()


            m =re .search (r'(?i)\b(?:referred\s*by|referring\s*doctor|prescribed\s*by)\s*[:=\t\s]+([A-Za-z\s\.\-_]+)',p_clean )
            if m and not meta ["referring_doctor"]:
                meta ["referring_doctor"]=m .group (1 ).strip ()

    return {k :v for k ,v in meta .items ()if v is not None and v !=""}


def extract_parameters_from_raw_items (raw_items :List [Dict [str ,Any ]])->List [Dict [str ,Any ]]:
    """Extracts and normalizes clinical parameters from structured list of items."""
    structured =[]
    seen =set ()

    for item in raw_items :
        param_name =str (item .get ("parameter","")).strip ()
        if not param_name or is_metadata_or_header_field (param_name ):
            continue 

        c_key ,meta =normalize_param_name (param_name )
        if not c_key or c_key in seen :
            continue 

        val_raw =item .get ("value_raw",item .get ("value"))
        num_val =parse_numeric_value (val_raw )

        if num_val is None or is_placeholder_value (val_raw ):
            continue 


        if num_val <0 :
            continue 

        raw_unit =str (item .get ("unit")or "").strip ()
        raw_ref =str (item .get ("reference_range")or "").strip ()

        unit_final =raw_unit or (meta ["unit"]if meta else "")
        ref_final =raw_ref or (meta ["ref_str"]if meta else "Reference range not provided")
        status =calculate_biomarker_status (num_val ,ref_final ,c_key ,str (item .get ("status","")))

        canonical_name =meta ["name"]if meta else param_name .title ()
        has_src_ref =bool (raw_ref )
        has_src_unit =bool (raw_unit )

        if has_src_ref and has_src_unit :
            confidence ="HIGH"
            reason ="Verified biomarker with report reference interval and unit"
        elif has_src_ref or has_src_unit :
            confidence ="HIGH"
            reason ="Matched standard biological range and unit"
        else :
            confidence ="MEDIUM"
            reason ="Biomarker identified; please verify unit and range"

        seen .add (c_key )
        structured .append ({
        "canonical_key":c_key ,
        "original_name":param_name ,
        "normalized_name":canonical_name ,
        "parameter":canonical_name ,
        "value":num_val ,
        "unit":unit_final ,
        "reference_range":ref_final ,
        "source_reference_range":raw_ref ,
        "status":status ,
        "confidence":confidence ,
        "confidence_reason":reason 
        })

    return structured 


def extract_parameters_from_text (raw_text :str )->List [Dict [str ,Any ]]:
    """
    Extracts laboratory biomarkers from raw text lines using:
    1. Multi-column spatial / delimiter table parsing (pipe, tab, multi-space).
    2. Suffix-isolated regex pattern matching (preventing numbers in biomarker names from polluting values).
    """
    found_items =[]
    lines =[line .strip ()for line in raw_text .splitlines ()if line .strip ()]
    sorted_aliases =sorted (PARAMETER_ALIASES .keys (),key =len ,reverse =True )

    for line in lines :
        line_clean =line .strip ()
        if not line_clean or line_clean .startswith ("=")or line_clean .startswith ("-")or line_clean .startswith ("_"):
            continue 


        m_ref_standalone =re .match (r'(?i)^(?:reference\s*range|ref\s*range|reference\s*interval|ref\s*interval|biological\s*reference\s*interval|bio\s*ref\s*interval)\s*[:=\t\s]+(.+)',line_clean )
        if m_ref_standalone and found_items :
            found_items [-1 ]["reference_range"]=m_ref_standalone .group (1 ).strip ()
            continue 

        m_stat_standalone =re .match (r'(?i)^(?:status|flag|interpretation|result\s*flag)\s*[:=\t\s]+(.+)',line_clean )
        if m_stat_standalone and found_items :
            found_items [-1 ]["status"]=m_stat_standalone .group (1 ).strip ().upper ()
            continue 


        clean_header_check =re .sub (r'[^a-zA-Z0-9\s]',' ',line_clean .lower ()).strip ()
        if is_metadata_or_header_field (clean_header_check ):
            continue 

        row_parsed =False 




        col_candidates =None 
        if "|"in line_clean :
            parts =[p .strip ()for p in line_clean .split ("|")if p .strip ()]
            if len (parts )>=2 :
                col_candidates =parts 
        elif "\t"in line_clean :
            parts =[p .strip ()for p in line_clean .split ("\t")if p .strip ()]
            if len (parts )>=2 :
                col_candidates =parts 
        else :
            space_parts =[p .strip ()for p in re .split (r'\s{2,}',line_clean .strip ())if p .strip ()]
            if len (space_parts )>=3 :
                col_candidates =space_parts 

        if col_candidates and len (col_candidates )>=2 :
            cand_name =col_candidates [0 ]
            c_key ,meta =normalize_param_name (cand_name )
            if c_key :
                val_raw =col_candidates [1 ].replace (",","").strip ()
                m_num =re .search (r'[-+]?\d+\.?\d*|[-+]?\.\d+',val_raw )
                if m_num :
                    val_float =float (m_num .group (0 ))
                    inline_unit =val_raw [m_num .end ():].strip ()

                    if inline_unit and not re .match (r'^\d',inline_unit ):
                        unit_str =inline_unit 
                        ref_str =col_candidates [2 ]if len (col_candidates )>2 else ""
                        status_str =col_candidates [3 ]if len (col_candidates )>3 else ""
                    else :
                        unit_str =col_candidates [2 ]if len (col_candidates )>2 else ""
                        ref_str =col_candidates [3 ]if len (col_candidates )>3 else ""
                        status_str =col_candidates [4 ]if len (col_candidates )>4 else ""

                    found_items .append ({
                    "parameter":cand_name ,
                    "canonical_key":c_key ,
                    "value_raw":val_float ,
                    "unit":unit_str ,
                    "reference_range":ref_str ,
                    "status":status_str 
                    })
                    row_parsed =True 

        if row_parsed :
            continue 




        matched_alias =None 
        matched_c_key =None 
        alias_span =None 

        for alias in sorted_aliases :
            pattern =rf'(?i)(?:^|[\s\(])({re .escape (alias )})(?:[\s\)]|$|[:=\t\-])'
            m =re .search (pattern ,line_clean )
            if m :
                matched_alias =alias 
                matched_c_key =PARAMETER_ALIASES [alias ]
                alias_span =m .span (1 )
                break 

        if not matched_alias or not alias_span :
            continue 


        suffix =line_clean [alias_span [1 ]:].lstrip (":= \t-")
        if not suffix :
            continue 


        m_ref =re .search (r'\(?(\d[\d,]*\.?\d*\s*(?:-|to|–|—)\s*\d[\d,]*\.?\d*\s*%?)\)?',suffix )
        if not m_ref :
            m_ref =re .search (r'\(?(<\s*[\d,]+\.?\d*|>\s*[\d,]+\.?\d*)\)?|\((\d[\d,]*\.?\d*\s*%)\)',suffix )

        clean_suffix =suffix 
        ref_found =""
        if m_ref :
            ref_found =(m_ref .group (1 )or m_ref .group (2 )or "").strip ()
            r_start ,r_end =m_ref .span (0 )
            clean_suffix =clean_suffix [:r_start ]+" "*(r_end -r_start )+clean_suffix [r_end :]


        m_status =re .search (r'\b(LOW|HIGH|NORMAL|CRITICAL|CRITICAL LOW|CRITICAL HIGH|ABNORMAL)\b',clean_suffix ,re .IGNORECASE )
        status_found =""
        if m_status :
            status_found =m_status .group (1 ).upper ()
            st_start ,st_end =m_status .span (1 )
            clean_suffix =clean_suffix [:st_start ]+" "*(st_end -st_start )+clean_suffix [st_end :]


        clean_suffix_no_commas =clean_suffix .replace (",","")
        m_val =re .search (r'[-+]?\d+\.?\d*|[-+]?\.\d+',clean_suffix_no_commas )
        if not m_val :
            continue 

        val_float =float (m_val .group (0 ))
        val_end =m_val .end ()
        after_val =clean_suffix_no_commas [val_end :].strip ()


        m_unit =re .match (r'^(?:U\s*\/\s*g\s*Hb|U\s*per\s*g\s*Hb|U\/gHb|U\/g_Hb|mg\s*\/\s*24h|ug\s*\/\s*24h|µg\s*\/\s*24h|cells\s*\/\s*[uµ]L|\/[uµ]L|mg\s*\/\s*dL|g\s*\/\s*dL|µg\s*\/\s*dL|ug\s*\/\s*dL|ng\s*\/\s*mL|pg\s*\/\s*mL|pmol\s*\/\s*L|mmol\s*\/\s*L|µIU\s*\/\s*mL|uIU\s*\/\s*mL|mIU\s*\/\s*L|U\s*\/\s*L|[a-zA-Z/%^0-9\-_µ]+)',after_val ,re .IGNORECASE )
        unit_str =m_unit .group (0 ).strip ()if m_unit else ""

        if val_float >=0 :
            found_items .append ({
            "parameter":matched_alias ,
            "canonical_key":matched_c_key ,
            "value_raw":val_float ,
            "unit":unit_str ,
            "reference_range":ref_found ,
            "status":status_found 
            })

    return extract_parameters_from_raw_items (found_items )



def extract_metadata_and_biomarkers (
raw_text :str ,
pre_parsed_items :Optional [List [Dict [str ,Any ]]]=None 
)->Tuple [Dict [str ,Any ],List [Dict [str ,Any ]]]:
    """
    Unified extraction pipeline:
    Extracts metadata, performs 2-phase parameter normalization, and calculates data quality metrics.
    """
    metadata =extract_metadata_from_lines (raw_text .splitlines ()if raw_text else [])

    if pre_parsed_items :
        parameters =extract_parameters_from_raw_items (pre_parsed_items )
    else :
        parameters =extract_parameters_from_text (raw_text )

    return metadata ,parameters 


def calculate_report_data_quality (
metadata :Dict [str ,Any ],
biomarkers :List [Dict [str ,Any ]]
)->Dict [str ,Any ]:
    """
    Computes objective data-quality metrics from extracted laboratory data:
    - biomarkers_detected: exact count of extracted biomarkers
    - reference_ranges_detected / reference_intervals_detected: count with reference ranges present or mapped
    - unmapped_parameters / unmapped_count: count of parameters without canonical key
    - missing_expected_parameters: count of core routine panel parameters absent
    - extraction_confidence: HIGH / MEDIUM / FAIR
    - overall_quality: GOOD / FAIR / POOR
    """
    bio_count =len (biomarkers )
    ranges_count =sum (
    1 for b in biomarkers 
    if (b .get ("reference_range")and str (b .get ("reference_range")).strip ()not in ["","None","-","Reference range not provided"])
    or (b .get ("canonical_key")and b .get ("canonical_key")in CANONICAL_REF_RANGES )
    )
    unmapped_count =sum (1 for b in biomarkers if not b .get ("canonical_key")or b .get ("canonical_key")=="UNKNOWN")

    CORE_ROUTINE_KEYS ={"HGB","RBC","WBC","PLT","TOTAL_BILIRUBIN","ALT","AST","TOTAL_PROTEIN","ALBUMIN"}
    present_keys ={b .get ("canonical_key")for b in biomarkers if b .get ("canonical_key")}
    missing_core =len (CORE_ROUTINE_KEYS -present_keys )


    if bio_count >=4 and (ranges_count /max (1 ,bio_count ))>=0.5 :
        confidence ="HIGH"
    elif bio_count >=2 :
        confidence ="MEDIUM"
    else :
        confidence ="FAIR"



    if confidence =="HIGH"and unmapped_count <=2 and bio_count >=3 :
        overall ="GOOD"
    elif bio_count >=2 and unmapped_count <=4 :
        overall ="FAIR"
    else :
        overall ="POOR"

    return {
    "biomarkers_detected":bio_count ,
    "reference_ranges_detected":ranges_count ,
    "reference_intervals_detected":ranges_count ,
    "unmapped_parameters":unmapped_count ,
    "unmapped_count":unmapped_count ,
    "missing_expected_parameters":missing_core ,
    "extraction_confidence":confidence ,
    "overall_quality":overall ,
    "has_patient_id":bool (metadata .get ("patient_id")),
    "has_patient_age":bool (metadata .get ("age")),
    "has_patient_gender":bool (metadata .get ("gender"))
    }
