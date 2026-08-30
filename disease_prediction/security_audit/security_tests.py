import os 
import sys 
import unittest 
import numpy as np 
import cv2 
from fastapi .testclient import TestClient 


current_dir =os .path .dirname (os .path .abspath (__file__ ))
parent_dir =os .path .abspath (os .path .join (current_dir ,'..'))
root_dir =os .path .abspath (os .path .join (current_dir ,'..','..'))
for d in [root_dir ,parent_dir ,current_dir ]:
    if d not in sys .path :
        sys .path .insert (0 ,d )

from disease_prediction .api .main import app ,generate_signed_token 
from disease_prediction .api import database as db 

client =TestClient (app )

class TestSecurityAudit (unittest .TestCase ):

    @classmethod 
    def setUpClass (cls ):
        db .init_db ()
        db .reset_to_clean_seed ()

        cls .admin_token =generate_signed_token ({"sub":"admin","role":"admin"})
        cls .patient_a_token =generate_signed_token ({"sub":"PAT-1001","role":"patient","patient_id":"PAT-1001"})
        cls .patient_b_token =generate_signed_token ({"sub":"PAT-1002","role":"patient","patient_id":"PAT-1002"})


    @classmethod 
    def tearDownClass (cls ):
        db .reset_to_clean_seed ()



    def test_01_unauthorized_patient_access_rejected (self ):

        res =client .get ("/api/reports?patient_id=PAT-1001")
        self .assertEqual (res .status_code ,401 )
        self .assertIn ("Authentication token required",res .json ()["detail"])


    def test_02_idor_cross_patient_report_access_rejected (self ):

        headers_a ={"Authorization":f"Bearer {self .patient_a_token }"}
        res_list =client .get ("/api/reports?patient_id=PAT-1002",headers =headers_a )
        self .assertEqual (res_list .status_code ,403 )
        self .assertIn ("Access denied",res_list .json ()["detail"])


        res_single =client .get ("/api/reports/REP-2026-002",headers =headers_a )
        self .assertEqual (res_single .status_code ,403 )


    def test_03_idor_cross_patient_prediction_access_rejected (self ):
        headers_a ={"Authorization":f"Bearer {self .patient_a_token }"}

        res =client .get ("/api/reports/REP-2026-002/predictions",headers =headers_a )
        self .assertEqual (res .status_code ,403 )


    def test_04_unauthorized_admin_endpoint_access_rejected (self ):

        headers_a ={"Authorization":f"Bearer {self .patient_a_token }"}
        res =client .get ("/api/patients",headers =headers_a )
        self .assertEqual (res .status_code ,403 )


        new_rep ={
        "patient_id":"PAT-1001",
        "test_category":"anemia",
        "report_data":{"HGB":10.0 }
        }
        res_post =client .post ("/api/reports",json =new_rep ,headers =headers_a )
        self .assertEqual (res_post .status_code ,403 )


    def test_05_invalid_report_id_handled (self ):
        headers_admin ={"Authorization":f"Bearer {self .admin_token }"}
        res =client .get ("/api/reports/NON_EXISTENT_REP_999",headers =headers_admin )
        self .assertEqual (res .status_code ,404 )


    def test_06_invalid_patient_login_rejected (self ):

        res =client .post ("/api/patient/login",json ={"patient_id":"PAT-1001","access_pin":"WRONG_PIN"})
        self .assertEqual (res .status_code ,401 )

        res_non =client .post ("/api/patient/login",json ={"patient_id":"PAT-9999","access_pin":"PIN-9999"})
        self .assertEqual (res_non .status_code ,401 )


    def test_07_sql_injection_defense (self ):
        sqli_payloads =[
        "' OR '1'='1",
        "'; DROP TABLE patients; --",
        "PAT-1001' UNION SELECT * FROM users --"
        ]
        for payload in sqli_payloads :
            res =client .post ("/api/patient/login",json ={"patient_id":payload ,"access_pin":"PIN-1001"})
            self .assertEqual (res .status_code ,401 )


    def test_08_malicious_non_image_upload_rejected (self ):
        fake_php_script =b"<?php echo 'malicious script payload'; ?>"*20 
        files ={"file":("shell.php.jpg",fake_php_script ,"image/jpeg")}
        res =client .post ("/predict/malaria",files =files )
        self .assertEqual (res .status_code ,400 )
        self .assertIn ("Corrupt or unreadable",res .json ()["detail"])



    def test_09_oversized_image_upload_rejected (self ):
        oversized_data =b"0"*(6 *1024 *1024 )
        files ={"file":("huge_smear.png",oversized_data ,"image/png")}
        res =client .post ("/predict/malaria",files =files )
        self .assertEqual (res .status_code ,400 )
        self .assertIn ("exceeds maximum",res .json ()["detail"])


    def test_10_invalid_negative_or_impossible_lab_values_rejected (self ):

        invalid_anemia ={
        "Age":28 ,
        "Sex":"Female",
        "HGB":-15.0 ,
        "RBC":4.2 ,
        "PCV":34.0 ,
        "MCV":70.0 ,
        "MCH":22.0 ,
        "MCHC":29.0 ,
        "RDW":15.0 ,
        "TLC":6.5 ,
        "PLT /mm3":200.0 
        }
        res =client .post ("/predict/anemia",json =invalid_anemia )
        self .assertEqual (res .status_code ,422 )


    def test_11_missing_lab_values_rejected_with_breakdown (self ):
        headers_admin ={"Authorization":f"Bearer {self .admin_token }"}
        incomplete_report ={
        "patient_id":"PAT-1001",
        "test_category":"thyroid",
        "report_data":{
        "TSH":25.0 

        }
        }
        res_create =client .post ("/api/reports",json =incomplete_report ,headers =headers_admin )
        rep_id =res_create .json ()["report_id"]

        headers_patient_a ={"Authorization":f"Bearer {self .patient_a_token }"}
        res_ml =client .post (f"/api/reports/{rep_id }/analyze-ml",headers =headers_patient_a )
        self .assertEqual (res_ml .status_code ,422 )
        err =res_ml .json ()["detail"]
        self .assertIn ("missing",err .lower ())
        self .assertIn ("T4",err )


    def test_12_official_report_remains_strictly_immutable_after_ml (self ):
        headers_admin ={"Authorization":f"Bearer {self .admin_token }"}
        headers_patient_a ={"Authorization":f"Bearer {self .patient_a_token }"}


        rep_before =client .get ("/api/reports/REP-2026-001",headers =headers_patient_a ).json ()
        orig_data =rep_before ["report_data"]
        orig_remarks =rep_before ["doctor_remarks"]


        res_ml =client .post ("/api/reports/REP-2026-001/analyze-ml",headers =headers_patient_a )
        self .assertEqual (res_ml .status_code ,200 )


        rep_after =client .get ("/api/reports/REP-2026-001",headers =headers_patient_a ).json ()
        self .assertEqual (rep_after ["report_data"],orig_data )
        self .assertEqual (rep_after ["doctor_remarks"],orig_remarks )
        self .assertEqual (rep_after ["status"],rep_before ["status"])


    def test_13_ml_prediction_integrity_and_disclaimer (self ):
        headers_patient_a ={"Authorization":f"Bearer {self .patient_a_token }"}
        res_preds =client .get ("/api/reports/REP-2026-001/predictions",headers =headers_patient_a )
        self .assertEqual (res_preds .status_code ,200 )
        preds =res_preds .json ()
        self .assertTrue (len (preds )>=1 )
        latest =preds [0 ]


        self .assertEqual (latest ["patient_id"],"PAT-1001")
        self .assertEqual (latest ["report_id"],"REP-2026-001")
        self .assertIn ("confidence",latest )
        self .assertIn ("model_used",latest )
        self .assertIn ("input_snapshot",latest )
        self .assertIn ("disclaimer",latest )
        self .assertIn ("educational and research",latest ["disclaimer"])


    def test_14_database_and_source_files_not_accessible_via_http (self ):
        res_db =client .get ("/pathology.db")

        self .assertIn (res_db .status_code ,[404 ,405 ])


    def test_15_database_backup_procedure (self ):
        backup_path =db .backup_database ()
        self .assertTrue (os .path .exists (backup_path ))
        self .assertTrue (os .path .getsize (backup_path )>0 )

if __name__ =="__main__":
    unittest .main ()
