"""
MEDLENS — Multi-Disease Rare & Unusual Condition Screening Engine
Modular clinical decision-support pattern recognition engine for rare and unusual pathologies.
Uses weighted multi-marker concordance scoring to evaluate combinations of laboratory abnormalities.

IMPORTANT CLINICAL SAFETY NOTICE:
This is an educational and clinical decision-support screening engine, NOT an autonomous diagnostic system.
It never declares a confirmed diagnosis from laboratory values alone.
"""

from typing import Dict ,Any ,List ,Optional ,Tuple 



RARE_DISEASE_KNOWLEDGE_BASE :List [Dict [str ,Any ]]=[



{
"id":"wilson_disease",
"name":"Possible Wilson Disease Pattern (Copper Transport Disorder)",
"short_name":"Wilson Disease",
"category":"Metabolic / Copper Transport Disorder",
"specialist":"Hepatologist / Medical Geneticist / Neurologist",
"primary_markers":[
{"key":"CERULOPLASMIN","expected":"LOW","weight":4.0 ,"label":"Ceruloplasmin (< 20 mg/dL)"},
{"key":"URINARY_COPPER_24H","expected":"HIGH","weight":4.0 ,"label":"24-Hour Urinary Copper (> 60 µg/24h)"},
{"key":"SERUM_COPPER","expected":"LOW","weight":2.5 ,"label":"Total Serum Copper (Low bound)"}
],
"supporting_markers":[
{"key":"ALT","expected":"HIGH","weight":1.5 ,"label":"ALT / SGPT (Transaminitis)"},
{"key":"AST","expected":"HIGH","weight":1.5 ,"label":"AST / SGOT (Transaminitis)"},
{"key":"TOTAL_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Total Bilirubin (Hyperbilirubinemia)"},
{"key":"INDIRECT_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Indirect Bilirubin (Hemolytic component)"},
{"key":"LDH","expected":"HIGH","weight":1.5 ,"label":"LDH (Intravascular Hemolysis marker)"},
{"key":"HAPTOGLOBIN","expected":"LOW","weight":1.5 ,"label":"Haptoglobin (Depleted in hemolysis)"},
{"key":"RETICULOCYTES","expected":"HIGH","weight":1.0 ,"label":"Reticulocyte Count (Compensatory erythropoiesis)"},
{"key":"ALBUMIN","expected":"LOW","weight":1.0 ,"label":"Albumin (Impaired hepatic synthesis)"}
],
"demographic_rules":[
{"field":"age","op":"lt","value":45 ,"weight":1.5 ,"label":"Young adult or pediatric presentation (Age < 45)"}
],
"contradictory_markers":[
{"key":"CERULOPLASMIN","expected":"HIGH","penalty":3.0 ,"label":"Elevated Ceruloplasmin contradicts classic Wilson deficiency"}
],
"required_primary_for_high":["CERULOPLASMIN","URINARY_COPPER_24H"],
"min_primary_for_high":2 ,
"thresholds":{"high":7.0 ,"moderate":4.5 ,"low":2.5 },
"why_flagged_template":"Multiple concordant laboratory findings (marked ceruloplasmin depression, elevated urinary copper excretion, transaminitis, and Coombs-negative hemolytic markers in a young individual) support a Wilson disease copper metabolism pattern and warrant confirmatory evaluation.",
"confirmatory_evaluation":[
"Ophthalmologic slit-lamp examination for Kayser-Fleischer (KF) corneal rings",
"Repeat 24-hour urinary copper excretion (with D-penicillamine challenge if equivocal)",
"Serum non-ceruloplasmin-bound (free) copper calculation",
"Targeted ATP7B gene mutation sequencing",
"Liver biopsy for quantitative hepatic copper measurement and histology when clinically indicated"
],
"missing_helpful_tests":[
"24-Hour Urinary Copper excretion",
"Serum Ceruloplasmin level",
"Slit-lamp ophthalmologic examination for Kayser-Fleischer rings",
"Targeted ATP7B gene sequencing"
]
},




{
"id":"hemochromatosis",
"name":"Possible Hereditary Hemochromatosis Pattern (Iron Overload)",
"short_name":"Hereditary Hemochromatosis",
"category":"Metabolic / Iron Storage Disorder",
"specialist":"Hepatologist / Hematologist / Geneticist",
"primary_markers":[
{"key":"TRANSFERRIN_SAT","expected":"HIGH","weight":4.0 ,"label":"Transferrin Saturation (> 50-60%)"},
{"key":"FERRITIN","expected":"HIGH","weight":3.5 ,"label":"Serum Ferritin (> 300-500 ng/mL)"},
{"key":"IRON","expected":"HIGH","weight":2.5 ,"label":"Serum Iron (Elevated)"}
],
"supporting_markers":[
{"key":"ALT","expected":"HIGH","weight":1.5 ,"label":"ALT / SGPT (Hepatic iron loading)"},
{"key":"AST","expected":"HIGH","weight":1.5 ,"label":"AST / SGOT (Hepatic iron loading)"},
{"key":"GLUCOSE","expected":"HIGH","weight":1.0 ,"label":"Fasting Glucose (Pancreatic endocrine siderosis)"},
{"key":"HBA1C","expected":"HIGH","weight":1.0 ,"label":"HbA1c (Secondary dysglycemia)"}
],
"contradictory_markers":[
{"key":"FERRITIN","expected":"LOW","penalty":4.0 ,"label":"Depleted Ferritin excludes iron overload"},
{"key":"TRANSFERRIN_SAT","expected":"LOW","penalty":3.5 ,"label":"Low Transferrin Saturation contradicts hemochromatosis"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Concordant elevation of transferrin saturation and serum ferritin in combination with hepatic enzyme elevation supports an iron overload pattern and warrants investigation for hereditary hemochromatosis.",
"confirmatory_evaluation":[
"HFE gene mutation analysis (C282Y and H63D variants)",
"Repeat fasting transferrin saturation and serum ferritin",
"Hepatic MRI T2* quantification for liver/cardiac iron concentration (LIC)",
"FibroScan (transient elastography) to evaluate hepatic fibrosis"
],
"missing_helpful_tests":[
"Fasting Transferrin Saturation (%)",
"Serum Ferritin",
"HFE gene mutation analysis"
]
},




{
"id":"alpha1_antitrypsin_deficiency",
"name":"Possible Alpha-1 Antitrypsin Deficiency Pattern (AATD)",
"short_name":"Alpha-1 Antitrypsin Deficiency",
"category":"Metabolic / Serpin Protease Inhibitor Disorder",
"specialist":"Pulmonologist / Hepatologist / Medical Geneticist",
"primary_markers":[
{"key":"ALPHA1_ANTITRYPSIN","expected":"LOW","weight":4.5 ,"label":"Alpha-1 Antitrypsin (< 90-100 mg/dL)"}
],
"supporting_markers":[
{"key":"ALT","expected":"HIGH","weight":1.5 ,"label":"ALT / SGPT (Transaminitis / Hepatic injury)"},
{"key":"AST","expected":"HIGH","weight":1.5 ,"label":"AST / SGOT (Transaminitis)"},
{"key":"TOTAL_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Total Bilirubin (Cholestatic / Hepatic jaundice)"},
{"key":"ALBUMIN","expected":"LOW","weight":1.0 ,"label":"Albumin (Decreased hepatic synthesis)"}
],
"contradictory_markers":[
{"key":"ALPHA1_ANTITRYPSIN","expected":"HIGH","penalty":4.0 ,"label":"Elevated Alpha-1 Antitrypsin (Acute phase response) contradicts genetic deficiency"}
],
"required_primary_for_high":["ALPHA1_ANTITRYPSIN"],
"min_primary_for_high":1 ,
"thresholds":{"high":5.5 ,"moderate":3.5 ,"low":2.0 },
"why_flagged_template":"Marked depression of serum Alpha-1 Antitrypsin level in combination with hepatic enzyme elevation supports an Alpha-1 Antitrypsin Deficiency (AATD) pattern and warrants confirmatory phenotyping and genetic analysis.",
"confirmatory_evaluation":[
"Alpha-1 Antitrypsin Phenotyping (Isoelectric focusing for Pi*Z and Pi*S alleles)",
"SERPINA1 gene targeted mutation analysis or full gene sequencing",
"High-resolution chest CT (HRCT) to assess for basal panacinar emphysema",
"Hepatic ultrasound / Transient Elastography (FibroScan) to assess liver stiffness"
],
"missing_helpful_tests":[
"Serum Alpha-1 Antitrypsin quantitative level",
"Alpha-1 Antitrypsin Pi-phenotyping",
"SERPINA1 gene sequencing"
]
},




{
"id":"g6pd_deficiency",
"name":"Possible G6PD Deficiency Pattern (Erythrocyte Enzymopathy)",
"short_name":"G6PD Deficiency",
"category":"Hematologic / Erythrocyte Enzymopathy",
"specialist":"Hematologist / Medical Geneticist",
"primary_markers":[
{"key":"G6PD_ENZYME_ACTIVITY","expected":"LOW","weight":5.0 ,"label":"G6PD Enzyme Activity (< 7.0 U/g Hb)"}
],
"supporting_markers":[
{"key":"LDH","expected":"HIGH","weight":2.0 ,"label":"LDH (Intravascular hemolysis marker)"},
{"key":"HAPTOGLOBIN","expected":"LOW","weight":2.0 ,"label":"Haptoglobin (Depleted < 30 mg/dL)"},
{"key":"INDIRECT_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Indirect Bilirubin (Unconjugated hyperbilirubinemia)"},
{"key":"RETICULOCYTES","expected":"HIGH","weight":1.5 ,"label":"Reticulocyte Count (Compensatory erythropoiesis)"},
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Acute hemolytic anemia)"}
],
"contradictory_markers":[
{"key":"G6PD_ENZYME_ACTIVITY","expected":"NORMAL","penalty":4.5 ,"label":"Normal G6PD enzyme activity contradicts active enzyme deficiency"},
{"key":"G6PD_ENZYME_ACTIVITY","expected":"HIGH","penalty":4.5 ,"label":"Elevated G6PD enzyme activity contradicts genetic enzyme deficiency"}
],
"required_primary_for_high":["G6PD_ENZYME_ACTIVITY"],
"min_primary_for_high":1 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Depressed quantitative G6PD enzyme activity indicates reduced erythrocyte antioxidant capacity, correlating with observed intravascular/extravascular hemolytic markers.",
"confirmatory_evaluation":[
"Quantitative spectrophotometric G6PD enzyme assay (performed or repeated 2-3 months after resolution of acute crisis)",
"Targeted G6PD gene sequencing for common endemic variants",
"Peripheral blood smear examination for bite cells and Heinz bodies",
"Direct Antiglobulin (Coombs) Test to rule out immune-mediated hemolytic anemia"
],
"missing_helpful_tests":[
"Quantitative G6PD spectrophotometric enzyme assay",
"Direct Antiglobulin Test (DAT / Coombs)",
"Peripheral blood smear review for bite cells"
]
},




{
"id":"hemolytic_anemia_generic",
"name":"Possible Hemolytic Anemia Pattern (Hemolytic Process)",
"short_name":"Hemolytic Anemia Pattern",
"category":"Hematologic / Hemolytic Disorder",
"specialist":"Hematologist",
"primary_markers":[
{"key":"LDH","expected":"HIGH","weight":3.0 ,"label":"LDH (Intravascular hemolysis biomarker)"},
{"key":"HAPTOGLOBIN","expected":"LOW","weight":3.0 ,"label":"Haptoglobin (Depleted < 30 mg/dL)"},
{"key":"INDIRECT_BILIRUBIN","expected":"HIGH","weight":2.5 ,"label":"Indirect Bilirubin (Unconjugated hyperbilirubinemia)"}
],
"supporting_markers":[
{"key":"RETICULOCYTES","expected":"HIGH","weight":2.0 ,"label":"Reticulocyte Count (Compensatory marrow response)"},
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Anemia)"},
{"key":"TOTAL_BILIRUBIN","expected":"HIGH","weight":1.0 ,"label":"Total Bilirubin (Hemolytic jaundice)"}
],
"contradictory_markers":[
{"key":"LDH","expected":"NORMAL","penalty":2.5 ,"label":"Normal LDH is atypical for active intravascular hemolysis"},
{"key":"HAPTOGLOBIN","expected":"HIGH","penalty":3.0 ,"label":"Elevated Haptoglobin contradicts acute intravascular hemolysis"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Concordant combination of elevated LDH, depleted haptoglobin, indirect hyperbilirubinemia, and reticulocytosis supports a hemolytic anemia pattern. Differential considerations include autoimmune hemolysis, enzymopathies (G6PD), membrane defects, or microangiopathy.",
"confirmatory_evaluation":[
"Direct and Indirect Antiglobulin (Coombs) Test (DAT)",
"Quantitative G6PD enzyme activity assay",
"Peripheral blood smear examination for schistocytes, spherocytes, or bite cells",
"Osmotic fragility test / Eosin-5-maleimide (EMA) binding"
],
"missing_helpful_tests":[
"Direct Antiglobulin (Coombs) Test",
"Quantitative G6PD enzyme assay",
"Peripheral blood film morphology"
]
},




{
"id":"multiple_myeloma",
"name":"Possible Multiple Myeloma / Monoclonal Gammopathy Pattern",
"short_name":"Multiple Myeloma Pattern",
"category":"Hematologic / Plasma Cell Dyscrasia",
"specialist":"Hematologist-Oncologist",
"primary_markers":[
{"key":"TOTAL_PROTEIN","expected":"HIGH","weight":3.0 ,"label":"Total Protein (Markedly elevated > 8.5 g/dL)"},
{"key":"GLOBULIN","expected":"HIGH","weight":3.0 ,"label":"Serum Globulin (Hypergammaglobulinemia)"},
{"key":"AG_RATIO","expected":"LOW","weight":2.5 ,"label":"A/G Ratio (Reversed / Severely Depressed < 0.8)"}
],
"supporting_markers":[
{"key":"CALCIUM","expected":"HIGH","weight":2.5 ,"label":"Serum Calcium (Hypercalcemia)"},
{"key":"CREATININE","expected":"HIGH","weight":2.0 ,"label":"Serum Creatinine (Myeloma nephropathy / renal impairment)"},
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Normocytic normochromic anemia)"},
{"key":"ESR","expected":"HIGH","weight":1.5 ,"label":"ESR (Markedly accelerated > 50-100 mm/hr)"},
{"key":"ALBUMIN","expected":"LOW","weight":1.0 ,"label":"Albumin (Depressed relative to globulins)"}
],
"contradictory_markers":[
{"key":"TOTAL_PROTEIN","expected":"LOW","penalty":2.5 ,"label":"Hypoproteinemia contradicts classic multiple myeloma pattern"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":7.0 ,"moderate":4.5 ,"low":2.5 },
"why_flagged_template":"Markedly elevated total protein with high globulin, reversed A/G ratio, hypercalcemia, normocytic anemia, and renal dysfunction forms a classic CRAB pattern warranting evaluation for plasma cell dyscrasia.",
"confirmatory_evaluation":[
"Serum Protein Electrophoresis (SPEP) and Immunofixation Electrophoresis (IFE)",
"Serum Free Light Chain (sFLC) assay (Kappa / Lambda ratio)",
"24-Hour Urine Protein Electrophoresis (UPEP) for Bence Jones protein",
"Bone marrow aspiration and biopsy with flow cytometry and cytogenetics (FISH)",
"Whole-body low-dose CT or skeletal survey for osteolytic lesions"
],
"missing_helpful_tests":[
"Serum Protein Electrophoresis (SPEP)",
"Serum Free Light Chains (sFLC)",
"Serum Calcium & Creatinine"
]
},




{
"id":"thalassemia_trait",
"name":"Possible Thalassemia Trait / Minor Pattern (Hemoglobinopathy)",
"short_name":"Thalassemia Trait",
"category":"Hematologic / Hemoglobin Synthesis Disorder",
"specialist":"Hematologist",
"primary_markers":[
{"key":"MCV","expected":"LOW","weight":3.5 ,"label":"MCV (Disproportionately low < 75 fL)"},
{"key":"MCH","expected":"LOW","weight":3.0 ,"label":"MCH (Markedly low < 25 pg)"},
{"key":"RBC","expected":"HIGH","weight":3.0 ,"label":"RBC Count (Preserved or elevated relative to anemia)"}
],
"supporting_markers":[
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Mild microcytic anemia or borderline)"},
{"key":"RDW","expected":"NORMAL","weight":1.5 ,"label":"RDW (Normal or minimally elevated, unlike iron deficiency)"},
{"key":"FERRITIN","expected":"NORMAL","weight":2.0 ,"label":"Serum Ferritin (Normal or elevated, excluding iron deficiency)"},
{"key":"IRON","expected":"NORMAL","weight":1.0 ,"label":"Serum Iron (Normal)"}
],
"contradictory_markers":[
{"key":"FERRITIN","expected":"LOW","penalty":2.5 ,"label":"Low Ferritin suggests Iron Deficiency Anemia rather than pure Thalassemia trait"},
{"key":"MCV","expected":"HIGH","penalty":4.0 ,"label":"Macrocytosis excludes beta-thalassemia trait"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Disproportionate microcytosis and hypochromia (marked low MCV/MCH) in the presence of a normal or elevated RBC count (Mentzer Index < 13) and normal ferritin supports a thalassemia trait pattern.",
"confirmatory_evaluation":[
"Hemoglobin High-Performance Liquid Chromatography (HPLC) or Hemoglobin Electrophoresis (HbA2 & HbF quantification)",
"Complete Iron Profile (Serum Iron, TIBC, Ferritin) to rule out concomitant iron deficiency",
"Alpha/Beta globin gene mutation analysis when indicated",
"Family screening and genetic counseling"
],
"missing_helpful_tests":[
"Hemoglobin HPLC / Electrophoresis (HbA2 quantification)",
"Complete Iron Studies (Ferritin, Iron, TIBC)"
]
},




{
"id":"addison_disease",
"name":"Possible Addison Disease / Adrenocortical Insufficiency Pattern",
"short_name":"Addison Disease Pattern",
"category":"Endocrine / Adrenocortical Disorder",
"specialist":"Endocrinologist",
"primary_markers":[
{"key":"SODIUM","expected":"LOW","weight":3.5 ,"label":"Sodium (Hyponatremia < 135 mmol/L)"},
{"key":"POTASSIUM","expected":"HIGH","weight":3.5 ,"label":"Potassium (Hyperkalemia > 5.0 mmol/L)"}
],
"supporting_markers":[
{"key":"GLUCOSE","expected":"LOW","weight":2.0 ,"label":"Fasting Glucose (Hypoglycemia / Low baseline)"},
{"key":"UREA","expected":"HIGH","weight":1.5 ,"label":"Blood Urea / BUN (Pre-renal azotemia / hypovolemia)"},
{"key":"CALCIUM","expected":"HIGH","weight":1.5 ,"label":"Serum Calcium (Mild hypercalcemia)"},
{"key":"EOSINOPHILS","expected":"HIGH","weight":1.0 ,"label":"Eosinophils (Relative eosinophilia)"}
],
"contradictory_markers":[
{"key":"POTASSIUM","expected":"LOW","penalty":3.5 ,"label":"Hypokalemia strongly contradicts primary adrenal insufficiency"},
{"key":"SODIUM","expected":"HIGH","penalty":3.5 ,"label":"Hypernatremia contradicts mineralocorticoid deficiency"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Concordant hyponatremia and hyperkalemia (low Na/K ratio < 30) combined with hypoglycemia and pre-renal azotemia supports an adrenocortical insufficiency pattern.",
"confirmatory_evaluation":[
"Morning (8 AM) Serum Cortisol and plasma ACTH (Adrenocorticotropic Hormone)",
"Cosyntropin (Synthetic ACTH) Stimulation Test",
"Serum Aldosterone and Plasma Renin Activity (PRA)",
"21-Hydroxylase autoantibodies",
"Adrenal gland CT imaging if non-autoimmune etiology suspected"
],
"missing_helpful_tests":[
"Morning (8 AM) Serum Cortisol & Plasma ACTH",
"Cosyntropin ACTH stimulation test",
"Serum Aldosterone / Renin ratio"
]
},




{
"id":"cushing_syndrome",
"name":"Possible Cushing Syndrome / Hypercortisolemia Pattern",
"short_name":"Cushing Syndrome Pattern",
"category":"Endocrine / Adrenal Hyperfunction",
"specialist":"Endocrinologist",
"primary_markers":[
{"key":"GLUCOSE","expected":"HIGH","weight":3.0 ,"label":"Fasting Glucose (Hyperglycemia / Steroid diabetes)"},
{"key":"POTASSIUM","expected":"LOW","weight":3.0 ,"label":"Potassium (Hypokalemia from mineralocorticoid crossover)"}
],
"supporting_markers":[
{"key":"SODIUM","expected":"HIGH","weight":1.5 ,"label":"Sodium (Hypernatremia / Fluid retention)"},
{"key":"HBA1C","expected":"HIGH","weight":1.5 ,"label":"HbA1c (Secondary insulin resistance)"},
{"key":"WBC","expected":"HIGH","weight":1.0 ,"label":"WBC Count (Glucocorticoid-induced leukocytosis/neutrophilia)"}
],
"contradictory_markers":[
{"key":"POTASSIUM","expected":"HIGH","penalty":3.0 ,"label":"Hyperkalemia contradicts hypercortisolemic state"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.0 ,"moderate":3.5 ,"low":2.5 },
"why_flagged_template":"Concordant hyperglycemia, hypokalemia, and hypernatremia support an endocrine hypercortisolemic pattern.",
"confirmatory_evaluation":[
"Overnight 1 mg Low-Dose Dexamethasone Suppression Test (LDDST)",
"24-Hour Urinary Free Cortisol (UFC) excretion (2 or more collections)",
"Late-night salivary cortisol measurements",
"Plasma ACTH measurement to differentiate ACTH-dependent vs. ACTH-independent causes"
],
"missing_helpful_tests":[
"Overnight 1 mg Dexamethasone suppression test",
"24-Hour Urinary Free Cortisol",
"Late-night salivary cortisol"
]
},




{
"id":"porphyria",
"name":"Possible Porphyria Pattern (Heme Biosynthesis Disorder)",
"short_name":"Porphyria Pattern",
"category":"Metabolic / Heme Biosynthesis Pathway Disorder",
"specialist":"Metabolic Geneticist / Hematologist / Hepatologist",
"primary_markers":[
{"key":"PORPHOBILINOGEN","expected":"HIGH","weight":5.0 ,"label":"Urinary Porphobilinogen / PBG (> 2.0 mg/24h)"}
],
"supporting_markers":[
{"key":"SODIUM","expected":"LOW","weight":2.0 ,"label":"Sodium (Hyponatremia / SIADH in acute neurovisceral attack)"},
{"key":"ALT","expected":"HIGH","weight":1.5 ,"label":"ALT (Hepatic porphyrin involvement)"},
{"key":"AST","expected":"HIGH","weight":1.5 ,"label":"AST (Transaminitis)"}
],
"contradictory_markers":[
{"key":"PORPHOBILINOGEN","expected":"NORMAL","penalty":4.0 ,"label":"Normal PBG during acute attack excludes acute porphyria"}
],
"required_primary_for_high":["PORPHOBILINOGEN"],
"min_primary_for_high":1 ,
"thresholds":{"high":6.0 ,"moderate":3.5 ,"low":2.0 },
"why_flagged_template":"Marked elevation of urinary porphobilinogen (PBG) in conjunction with hyponatremia and transaminitis supports an acute hepatic porphyria pattern.",
"confirmatory_evaluation":[
"Quantitative urine porphobilinogen (PBG) and delta-aminolevulinic acid (ALA)",
"Fractionated plasma and fecal porphyrin profile",
"Hydroxymethylbilane Synthase (HMBS) enzymatic assay and gene sequencing",
"Clinical correlation for acute neurovisceral abdominal pain and photosensitivity"
],
"missing_helpful_tests":[
"Quantitative Urine Porphobilinogen (PBG)",
"Delta-Aminolevulinic Acid (ALA)",
"Plasma & Fecal porphyrin fractionation"
]
},




{
"id":"autoimmune_hepatitis",
"name":"Possible Autoimmune Hepatitis Pattern",
"short_name":"Autoimmune Hepatitis Pattern",
"category":"Hepatic / Autoimmune Liver Disease",
"specialist":"Hepatologist / Gastroenterologist",
"primary_markers":[
{"key":"ALT","expected":"HIGH","weight":3.0 ,"label":"ALT / SGPT (Marked transaminitis)"},
{"key":"AST","expected":"HIGH","weight":3.0 ,"label":"AST / SGOT (Marked transaminitis)"},
{"key":"GLOBULIN","expected":"HIGH","weight":3.5 ,"label":"Total Globulin (Hypergammaglobulinemia)"}
],
"supporting_markers":[
{"key":"IGG","expected":"HIGH","weight":2.5 ,"label":"Serum IgG (Elevated immunoglobulin fraction)"},
{"key":"TOTAL_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Total Bilirubin (Jaundice)"},
{"key":"DIRECT_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Direct Bilirubin (Conjugated fraction)"},
{"key":"AG_RATIO","expected":"LOW","weight":1.5 ,"label":"A/G Ratio (Depressed < 1.0)"},
{"key":"ALP","expected":"NORMAL","weight":1.0 ,"label":"ALP (Normal or mildly elevated, AST/ALT >> ALP)"}
],
"contradictory_markers":[
{"key":"ALT","expected":"NORMAL","penalty":4.0 ,"label":"Normal ALT contradicts active autoimmune hepatitis"},
{"key":"GLOBULIN","expected":"NORMAL","penalty":3.0 ,"label":"Normal globulin is atypical for active autoimmune hepatitis"}
],
"required_primary_for_high":["GLOBULIN"],
"min_primary_for_high":3 ,
"thresholds":{"high":7.5 ,"moderate":5.0 ,"low":3.0 },
"why_flagged_template":"Markedly elevated transaminases (ALT/AST) in combination with hypergammaglobulinemia (high globulin, low A/G ratio) and hyperbilirubinemia supports an autoimmune hepatitis pattern.",
"confirmatory_evaluation":[
"Autoantibody panel: Antinuclear Antibodies (ANA), Smooth Muscle Antibodies (ASMA / Anti-Actin), Anti-LKM-1, and Anti-SLA",
"Quantitative serum IgG immunoglobulin level",
"Viral hepatitis serologies (HBsAg, Anti-HCV, Anti-HAV, Anti-HEV) to rule out viral causes",
"Liver biopsy to assess interface hepatitis, lymphoplasmacytic infiltrate, and staging"
],
"missing_helpful_tests":[
"Autoantibody panel (ANA, ASMA, Anti-LKM1)",
"Quantitative Serum IgG level",
"Viral hepatitis serologies (HBsAg, Anti-HCV)"
]
},




{
"id":"primary_biliary_cholangitis",
"name":"Possible Primary Biliary Cholangitis Pattern (Cholestatic)",
"short_name":"Primary Biliary Cholangitis Pattern",
"category":"Hepatic / Autoimmune Cholestatic Disease",
"specialist":"Hepatologist / Gastroenterologist",
"primary_markers":[
{"key":"ALP","expected":"HIGH","weight":4.0 ,"label":"Alkaline Phosphatase (Markedly elevated cholestatic enzyme)"},
{"key":"DIRECT_BILIRUBIN","expected":"HIGH","weight":2.5 ,"label":"Direct Bilirubin (Cholestatic hyperbilirubinemia)"}
],
"supporting_markers":[
{"key":"GLOBULIN","expected":"HIGH","weight":2.0 ,"label":"Globulin (Elevated serum IgM fraction)"},
{"key":"TOTAL_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Total Bilirubin (Elevated)"},
{"key":"ALT","expected":"HIGH","weight":1.0 ,"label":"ALT (Mild to moderate transaminitis; ALP >> ALT)"},
{"key":"AST","expected":"HIGH","weight":1.0 ,"label":"AST (Mild to moderate elevation)"}
],
"demographic_rules":[
{"field":"gender","op":"eq","value":"Female","weight":1.0 ,"label":"Predominantly female demographic"}
],
"contradictory_markers":[
{"key":"ALP","expected":"NORMAL","penalty":4.0 ,"label":"Normal ALP strongly contradicts primary biliary cholangitis"}
],
"min_primary_for_high":1 ,
"thresholds":{"high":6.0 ,"moderate":3.5 ,"low":2.5 },
"why_flagged_template":"Predominant alkaline phosphatase elevation with cholestatic hyperbilirubinemia and elevated globulins supports a cholestatic liver disease pattern compatible with primary biliary cholangitis.",
"confirmatory_evaluation":[
"Anti-Mitochondrial Antibodies (AMA / AMA-M2 titer)",
"PBC-specific ANA markers (Anti-sp100, Anti-gp210)",
"Serum IgM level quantification",
"Abdominal and biliary ultrasound / Magnetic Resonance Cholangiopancreatography (MRCP) to exclude extrahepatic biliary obstruction"
],
"missing_helpful_tests":[
"Anti-Mitochondrial Antibodies (AMA / AMA-M2)",
"Serum IgM quantification",
"Biliary MRCP / Ultrasound"
]
},




{
"id":"hereditary_spherocytosis",
"name":"Possible Hereditary Spherocytosis Pattern (RBC Membrane Defect)",
"short_name":"Hereditary Spherocytosis Pattern",
"category":"Hematologic / Erythrocyte Membrane Disorder",
"specialist":"Hematologist",
"primary_markers":[
{"key":"MCHC","expected":"HIGH","weight":4.0 ,"label":"MCHC (Hyperchromic erythrocytes > 35.5 g/dL)"},
{"key":"RETICULOCYTES","expected":"HIGH","weight":3.0 ,"label":"Reticulocyte Count (Prominent reticulocytosis)"}
],
"supporting_markers":[
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Hemolytic anemia)"},
{"key":"INDIRECT_BILIRUBIN","expected":"HIGH","weight":2.0 ,"label":"Indirect Bilirubin (Chronic extravascular hemolysis)"},
{"key":"LDH","expected":"HIGH","weight":1.5 ,"label":"LDH (Elevated lactate dehydrogenase)"},
{"key":"HAPTOGLOBIN","expected":"LOW","weight":1.5 ,"label":"Haptoglobin (Depleted)"},
{"key":"RDW","expected":"HIGH","weight":1.0 ,"label":"RDW (Elevated anisocytosis)"}
],
"contradictory_markers":[
{"key":"MCHC","expected":"LOW","penalty":4.0 ,"label":"Hypochromia (Low MCHC) contradicts spherocytosis"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":6.5 ,"moderate":4.0 ,"low":2.5 },
"why_flagged_template":"Elevated MCHC (> 35.5 g/dL) in combination with reticulocytosis, indirect hyperbilirubinemia, and hemolytic markers supports a hereditary spherocytosis or extravascular hemolytic pattern.",
"confirmatory_evaluation":[
"Eosin-5-maleimide (EMA) binding test by flow cytometry",
"Osmotic fragility test",
"Peripheral blood smear examination for microspherocytes and lack of central pallor",
"Direct Antiglobulin Test (DAT) to rule out autoimmune hemolytic anemia (AIHA)"
],
"missing_helpful_tests":[
"EMA binding test by flow cytometry",
"Osmotic fragility test",
"Peripheral blood smear morphology for spherocytes"
]
},




{
"id":"thrombotic_microangiopathy",
"name":"Possible Thrombotic Microangiopathy Pattern (TTP / HUS / TMA)",
"short_name":"Thrombotic Microangiopathy Pattern",
"category":"Hematologic / Microvascular Thrombotic Disorder",
"specialist":"Hematologist / Nephrologist / Critical Care",
"primary_markers":[
{"key":"PLT","expected":"LOW","weight":3.5 ,"label":"Platelet Count (Consumptive thrombocytopenia < 100,000 /µL)"},
{"key":"LDH","expected":"HIGH","weight":3.0 ,"label":"LDH (Marked microangiopathic hemolysis)"},
{"key":"HAPTOGLOBIN","expected":"LOW","weight":2.5 ,"label":"Haptoglobin (Depleted)"}
],
"supporting_markers":[
{"key":"CREATININE","expected":"HIGH","weight":2.0 ,"label":"Serum Creatinine (Renal microvascular impairment)"},
{"key":"INDIRECT_BILIRUBIN","expected":"HIGH","weight":1.5 ,"label":"Indirect Bilirubin (Hemolysis)"},
{"key":"HGB","expected":"LOW","weight":1.5 ,"label":"Hemoglobin (Microangiopathic hemolytic anemia)"}
],
"contradictory_markers":[
{"key":"PLT","expected":"NORMAL","penalty":4.0 ,"label":"Normal platelets exclude acute thrombotic microangiopathy"}
],
"min_primary_for_high":2 ,
"thresholds":{"high":7.0 ,"moderate":4.5 ,"low":2.5 },
"why_flagged_template":"Concordant consumptive thrombocytopenia, marked LDH elevation, depleted haptoglobin, and renal dysfunction forms a classic microangiopathic pattern requiring urgent evaluation for TTP / HUS.",
"confirmatory_evaluation":[
"Peripheral blood smear examination for schistocytes (fragmented RBCs > 1%)",
"ADAMTS13 activity and inhibitor antibody titer",
"Direct Antiglobulin (Coombs) Test (typically negative in TMA)",
"Serum complement panel (C3, C4, CH50, anti-factor H antibodies) if atypical HUS suspected"
],
"missing_helpful_tests":[
"Peripheral blood smear for schistocytes / helmet cells",
"ADAMTS13 activity and inhibitor level",
"Direct Antiglobulin (Coombs) Test"
]
}
]


def evaluate_biomarker_condition (
expected_status :str ,
actual_status :str ,
actual_val :Optional [float ]
)->bool :
    """Evaluates whether an extracted biomarker matches expected direction."""
    expected_status =expected_status .upper ()
    actual_status =actual_status .upper ()

    if expected_status =="HIGH":
        return actual_status in ["HIGH","CRITICAL HIGH","CRITICAL","ABNORMAL"]
    elif expected_status =="LOW":
        return actual_status in ["LOW","CRITICAL LOW","CRITICAL","ABNORMAL"]
    elif expected_status =="NORMAL":
        return actual_status =="NORMAL"

    return False 


def evaluate_rare_disease_patterns (
parameters :List [Dict [str ,Any ]],
patient_meta :Optional [Dict [str ,Any ]]=None 
)->Dict [str ,Any ]:
    """
    Evaluates multi-marker concordance across all defined rare/unusual disease profiles.
    Returns structured decision-support screening results, ranked candidate cards,
    unsupported conditions audit, and missing helpful diagnostic tests.
    """
    patient_meta =patient_meta or {}
    age =patient_meta .get ("age")
    try :
        age_val =float (age )if age is not None else None 
    except (ValueError ,TypeError ):
        age_val =None 

    gender =str (patient_meta .get ("gender")or "").strip ().capitalize ()


    param_map :Dict [str ,Dict [str ,Any ]]={}
    for p in parameters :
        c_key =str (p .get ("canonical_key","")).upper ().strip ()
        p_name =str (p .get ("parameter","")).upper ().strip ()
        norm_name =str (p .get ("normalized_name","")).upper ().strip ()
        orig_name =str (p .get ("original_name","")).upper ().strip ()
        for k in [c_key ,p_name ,norm_name ,orig_name ]:
            if k :
                param_map [k ]=p 


        if c_key in ["G6PD","G6PD_ENZYME_ACTIVITY"]:
            param_map ["G6PD_ENZYME_ACTIVITY"]=p 
            param_map ["G6PD"]=p 
        elif c_key in ["ALPHA1_ANTITRYPSIN","ALPHA_1_ANTITRYPSIN","AAT"]:
            param_map ["ALPHA1_ANTITRYPSIN"]=p 
            param_map ["ALPHA_1_ANTITRYPSIN"]=p 
            param_map ["AAT"]=p 
        elif c_key in ["URINARY_COPPER_24H","URINE_COPPER_24H","24_HOUR_URINARY_COPPER"]:
            param_map ["URINARY_COPPER_24H"]=p 
            param_map ["URINE_COPPER_24H"]=p 
        elif c_key in ["TRANSFERRIN_SAT","TRANSFERRIN_SATURATION","TSAT"]:
            param_map ["TRANSFERRIN_SAT"]=p 
            param_map ["TRANSFERRIN_SATURATION"]=p 
        elif c_key in ["PORPHOBILINOGEN","URINARY_PORPHOBILINOGEN","PBG"]:
            param_map ["PORPHOBILINOGEN"]=p 
            param_map ["URINARY_PORPHOBILINOGEN"]=p 
        elif c_key in ["PLT","PLATELET_COUNT","PLATELETS"]:
            param_map ["PLT"]=p 
            param_map ["PLATELET_COUNT"]=p 
        elif c_key in ["WBC","TLC","WHITE_BLOOD_CELL_COUNT"]:
            param_map ["WBC"]=p 
            param_map ["TLC"]=p 
        elif c_key in ["HGB","HEMOGLOBIN","HB"]:
            param_map ["HGB"]=p 
            param_map ["HEMOGLOBIN"]=p 

    evaluated_conditions =[]
    unsupported_conditions =[]

    for profile in RARE_DISEASE_KNOWLEDGE_BASE :
        disease_id =profile ["id"]
        disease_name =profile ["name"]
        short_name =profile ["short_name"]
        category =profile ["category"]
        specialist =profile ["specialist"]

        score =0.0 
        primary_matches =[]
        supporting_matches =[]
        missing_markers =[]
        contradictory_matches =[]


        for pm in profile .get ("primary_markers",[]):
            k =pm ["key"]
            p_obj =param_map .get (k )
            if p_obj :
                val =p_obj .get ("value")
                st =str (p_obj .get ("status","NORMAL")).upper ()
                if evaluate_biomarker_condition (pm ["expected"],st ,val ):
                    score +=pm ["weight"]
                    primary_matches .append ({
                    "key":k ,
                    "biomarker":p_obj .get ("parameter",k ),
                    "value":f"{val } {p_obj .get ('unit','')}".strip (),
                    "status":st ,
                    "expected":pm ["expected"],
                    "importance":"Primary Disease-Specific Marker",
                    "label":pm ["label"]
                    })
            else :
                missing_markers .append (pm ["label"])


        for sm in profile .get ("supporting_markers",[]):
            k =sm ["key"]
            p_obj =param_map .get (k )
            if p_obj :
                val =p_obj .get ("value")
                st =str (p_obj .get ("status","NORMAL")).upper ()
                if evaluate_biomarker_condition (sm ["expected"],st ,val ):
                    score +=sm ["weight"]
                    supporting_matches .append ({
                    "key":k ,
                    "biomarker":p_obj .get ("parameter",k ),
                    "value":f"{val } {p_obj .get ('unit','')}".strip (),
                    "status":st ,
                    "expected":sm ["expected"],
                    "importance":"Supporting Concordant Marker",
                    "label":sm ["label"]
                    })
            else :
                missing_markers .append (sm ["label"])


        for dr in profile .get ("demographic_rules",[]):
            field =dr ["field"]
            if field =="age"and age_val is not None :
                if dr ["op"]=="lt"and age_val <dr ["value"]:
                    score +=dr ["weight"]
                    supporting_matches .append ({
                    "biomarker":f"Patient Age ({int (age_val )} Yrs)",
                    "value":f"{int (age_val )} Yrs",
                    "status":"CONCORDANT",
                    "expected":f"< {dr ['value']} Yrs",
                    "importance":"Demographic Context",
                    "label":dr ["label"]
                    })
            elif field =="gender"and gender :
                if dr ["op"]=="eq"and gender ==dr ["value"]:
                    score +=dr ["weight"]
                    supporting_matches .append ({
                    "biomarker":f"Patient Gender ({gender })",
                    "value":gender ,
                    "status":"CONCORDANT",
                    "expected":dr ["value"],
                    "importance":"Demographic Context",
                    "label":dr ["label"]
                    })


        for cm in profile .get ("contradictory_markers",[]):
            k =cm ["key"]
            p_obj =param_map .get (k )
            if p_obj :
                val =p_obj .get ("value")
                st =str (p_obj .get ("status","NORMAL")).upper ()
                if evaluate_biomarker_condition (cm ["expected"],st ,val ):
                    score -=cm ["penalty"]
                    contradictory_matches .append (cm ["label"])


        thresholds =profile ["thresholds"]
        min_prim =profile .get ("min_primary_for_high",1 )
        required_keys =profile .get ("required_primary_for_high",[])
        matched_primary_keys ={m .get ("key")for m in primary_matches if "key"in m }
        has_all_required =(all (rk in matched_primary_keys for rk in required_keys )if required_keys else True )

        why_text =profile ["why_flagged_template"]


        if score >=thresholds ["high"]and len (primary_matches )>=min_prim and has_all_required and not contradictory_matches :
            screening_strength ="HIGH"
            concordance_tier ="Strong"
        elif score >=thresholds ["moderate"]and len (primary_matches )>=1 and (has_all_required or not required_keys )and not (len (contradictory_matches )>=2 ):
            screening_strength ="MODERATE"
            concordance_tier ="Moderate"
            if required_keys and not has_all_required :
                missing_req =[rk .replace ('_',' ').title ()for rk in required_keys if rk not in matched_primary_keys ]
                why_text =f"Partial {profile ['short_name']} pattern identified. Key confirmatory biomarker(s) ({', '.join (missing_req )}) are unavailable from this report, warranting confirmatory testing."
        elif score >=thresholds ["low"]and len (primary_matches )>=1 and (has_all_required or not required_keys )and not contradictory_matches :
            screening_strength ="LOW"
            concordance_tier ="Limited"
            why_text =f"Limited evidence for {profile ['short_name']}. Important supporting biomarkers are unavailable."
        else :
            screening_strength ="NONE"
            concordance_tier ="Insufficient"


        prim_tot =len (profile .get ("primary_markers",[]))
        supp_tot =len (profile .get ("supporting_markers",[]))
        prim_cnt =len (primary_matches )
        supp_cnt =len (supporting_matches )
        contra_cnt =len (contradictory_matches )

        if screening_strength =="HIGH":
            concordance_pct =min (96 ,max (76 ,int (60 +score *2.8 )))
        elif screening_strength =="MODERATE":
            concordance_pct =min (74 ,max (46 ,int (35 +score *2.8 )))
        elif screening_strength =="LOW":
            concordance_pct =min (44 ,max (22 ,int (15 +score *2.8 )))
        else :
            concordance_pct =0 

        if screening_strength !="NONE"and prim_cnt >=1 :
            all_supporting =primary_matches +supporting_matches 
            evaluated_conditions .append ({
            "disease_id":disease_id ,
            "name":disease_name ,
            "short_name":short_name ,
            "condition":disease_name ,
            "category":category ,
            "screening_strength":screening_strength ,
            "strength":screening_strength ,
            "concordance_tier":concordance_tier ,
            "concordance_score":round (score ,1 ),
            "concordance_pct":concordance_pct ,
            "evidence_count":len (all_supporting ),
            "primary_matches_count":prim_cnt ,
            "primary_total":prim_tot ,
            "primary_ratio":f"{prim_cnt }/{prim_tot }",
            "supporting_matches_count":supp_cnt ,
            "supporting_total":supp_tot ,
            "supporting_ratio":f"{supp_cnt }/{supp_tot }",
            "contradictory_count":contra_cnt ,
            "contradictory_matched":contradictory_matches ,
            "primary_matched":primary_matches ,
            "supporting_matched":supporting_matches ,
            "why_flagged":why_text ,
            "supporting_findings":[f"{m ['biomarker']}: {m ['value']} ({m ['status']})"for m in all_supporting ],
            "findings_matched":[f"{m ['biomarker']}: {m ['value']} ({m ['status']})"for m in all_supporting ],
            "detailed_findings":all_supporting ,
            "missing_or_contradictory":contradictory_matches ,
            "confirmatory_evaluation":profile ["confirmatory_evaluation"],
            "missing_helpful_tests":profile .get ("missing_helpful_tests",[]),
            "specialist":specialist ,
            "disclaimer":"Screening signal only — laboratory screening alone does NOT establish or confirm a diagnosis. Comprehensive specialist clinical correlation is required."
            })
        else :

            evidence_checked =[]
            for pm in profile .get ("primary_markers",[]):
                k =pm ["key"]
                p_obj =param_map .get (k )
                if p_obj :
                    val =p_obj .get ("value")
                    st =str (p_obj .get ("status","NORMAL")).upper ()
                    unit =p_obj .get ("unit","")
                    evidence_checked .append ({
                    "biomarker":p_obj .get ("parameter",pm ["label"]),
                    "status_text":f"{st .lower ()} ({val } {unit })".strip (),
                    "available":True ,
                    "status":st 
                    })
                else :
                    evidence_checked .append ({
                    "biomarker":pm ["label"],
                    "status_text":"Not available in report",
                    "available":False ,
                    "status":"NOT_AVAILABLE"
                    })


            has_any_related =any (
            param_map .get (sm ["key"])is not None 
            for sm in profile .get ("supporting_markers",[])[:3 ]
            )or any (ec ["available"]for ec in evidence_checked )

            if has_any_related :
                unsupported_conditions .append ({
                "disease_id":disease_id ,
                "name":disease_name ,
                "short_name":short_name ,
                "category":category ,
                "status_label":f"{short_name } — NOT STRONGLY SUPPORTED",
                "reason":f"Evaluated laboratory parameters do not meet multi-marker concordance criteria for {short_name }.",
                "evidence_checked":evidence_checked ,
                "missing_helpful_tests":profile .get ("missing_helpful_tests",[])
                })


    evaluated_conditions .sort (key =lambda x :(
    0 if x ["screening_strength"]=="HIGH"else (1 if x ["screening_strength"]=="MODERATE"else 2 ),
    -x ["concordance_score"]
    ))

    is_flagged =(len (evaluated_conditions )>0 and any (c ["screening_strength"]in ["HIGH","MODERATE"]for c in evaluated_conditions ))
    top_condition =evaluated_conditions [0 ]if is_flagged else None 


    top_patterns =[
    {
    "rank":idx +1 ,
    "name":c ["short_name"],
    "full_name":c ["name"],
    "strength":c ["screening_strength"],
    "concordance_pct":c .get ("concordance_pct",50 ),
    "tier":c ["concordance_tier"],
    "why_flagged":c ["why_flagged"],
    "primary_ratio":c .get ("primary_ratio","1/1"),
    "supporting_ratio":c .get ("supporting_ratio","1/1")
    }
    for idx ,c in enumerate (evaluated_conditions [:3 ])
    ]


    helpful_missing =[]
    seen_tests =set ()
    for c in evaluated_conditions [:3 ]:
        for t in c .get ("missing_helpful_tests",[]):
            if t not in seen_tests :
                seen_tests .add (t )
                helpful_missing .append (t )


    if not helpful_missing and unsupported_conditions :
        for uc in unsupported_conditions [:2 ]:
            for t in uc .get ("missing_helpful_tests",[]):
                if t not in seen_tests :
                    seen_tests .add (t )
                    helpful_missing .append (t )



    alt =param_map .get ("ALT")
    ast =param_map .get ("AST")
    has_isolated_transaminitis =(
    (alt and str (alt .get ("status","")).upper ()in ["HIGH","CRITICAL HIGH"])or 
    (ast and str (ast .get ("status","")).upper ()in ["HIGH","CRITICAL HIGH"])
    )
    if not is_flagged and has_isolated_transaminitis :
        why_text_fallback =(
        "Non-specific hepatocellular transaminitis detected (elevated ALT/AST). "
        "Evaluated rare metabolic/autoimmune etiologies (Wilson disease, Hemochromatosis, Alpha-1 Antitrypsin Deficiency) "
        "do not meet multi-marker concordance criteria due to absence or normal values of disease-specific markers."
        )
    elif not is_flagged :
        why_text_fallback ="No sufficiently specific multi-marker pattern was identified from the available laboratory data."
    else :
        why_text_fallback =top_condition ["why_flagged"]

    return {
    "flagged":is_flagged ,
    "top_condition":top_condition ,
    "conditions_count":len (evaluated_conditions ),
    "conditions":evaluated_conditions ,
    "top_screening_patterns":top_patterns ,
    "unsupported_conditions":unsupported_conditions [:4 ],
    "missing_helpful_tests":helpful_missing [:5 ],

    "condition_name":top_condition ["name"]if top_condition else "No specific rare condition identified",
    "screening_strength":top_condition ["screening_strength"]if top_condition else "NONE",
    "why_flagged":why_text_fallback ,
    "supporting_findings":top_condition ["supporting_findings"]if top_condition else ["No rare disease multi-marker pattern criteria met."],
    "confirmatory_evaluation":top_condition ["confirmatory_evaluation"][0 ]if top_condition else "Periodic wellness review with primary healthcare provider.",
    "disclaimer":"AI-assisted screening for potential uncommon conditions based on available laboratory findings only — not an autonomous medical diagnosis. Definitive confirmation requires clinical correlation, history, physical examination, and specialist diagnostic evaluation."
    }
