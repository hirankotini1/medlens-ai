"""
Nexus Pathology — Automated Patient & Report Persistence Test Suite
Tests:
1. Patient Registration & Database Persistence (POST /api/patients -> SELECT from SQLite)
2. AI Health Report Creation & Association (POST /api/analyzer/analyze -> lab_reports & report_analyses)
3. Simulated Page Refresh (GET /api/patients, GET /api/patients/public, GET /api/reports)
4. Multi-Patient Isolation (PERSIST-001 vs PERSIST-002)
5. Patient Portal Authentication with Generated PIN & Isolated Report Access
6. Direct SQLite Database Table Invariant Verification
"""

import urllib .request 
import urllib .error 
import json 
import sqlite3 
import os 
import sys 

BASE_URL ="http://127.0.0.1:8000"
DB_PATH =os .path .abspath (os .path .join (os .path .dirname (__file__ ),"pathology.db"))

def make_req (path ,method ="GET",data =None ,token =None ):
    url =f"{BASE_URL }{path }"
    headers ={"Content-Type":"application/json"}
    if token :
        headers ["Authorization"]=f"Bearer {token }"

    req_body =json .dumps (data ).encode ("utf-8")if data else None 
    req =urllib .request .Request (url ,data =req_body ,headers =headers ,method =method )
    try :
        with urllib .request .urlopen (req ,timeout =30 )as resp :
            body =resp .read ().decode ("utf-8")
            return resp .status ,json .loads (body )if body else {}
    except urllib .error .HTTPError as e :
        body =e .read ().decode ("utf-8")
        return e .code ,json .loads (body )if body else {}

def test_persistence_flow ():
    print ("="*80 )
    print ("      NEXUS PATHOLOGY — PATIENT & REPORT PERSISTENCE VERIFICATION")
    print ("="*80 )


    status ,auth_res =make_req ("/api/auth/login",method ="POST",data ={"username":"admin","password":"admin123"})
    assert status ==200 ,f"Admin login failed: {auth_res }"
    admin_token =auth_res ["token"]
    print ("\n[STEP 1] Admin Authenticated Successfully.")


    pat1_payload ={
    "patient_id":"PERSIST-001",
    "name":"Persistence Test Patient",
    "age":30 ,
    "gender":"Male",
    "contact":"+91-9988776655",
    "email":"persist1@test.com",
    "access_pin":"PIN-001"
    }
    status ,pat1_res =make_req ("/api/patients",method ="POST",data =pat1_payload ,token =admin_token )
    assert status ==200 ,f"Failed to create PERSIST-001: {pat1_res }"
    print (f"[STEP 2] Created Patient: {pat1_res ['patient_id']} ({pat1_res ['name']}) with PIN: {pat1_res .get ('generated_pin')}")


    analyzer_payload_1 ={
    "parameters":[
    {"parameter":"Hemoglobin","value":10.2 ,"unit":"g/dL","reference_range":"13.0 - 17.0","status":"LOW"},
    {"parameter":"Total Bilirubin","value":4.5 ,"unit":"mg/dL","reference_range":"0.2 - 1.2","status":"HIGH"},
    {"parameter":"Direct Bilirubin","value":1.9 ,"unit":"mg/dL","reference_range":"0.0 - 0.3","status":"HIGH"},
    {"parameter":"Serum Ceruloplasmin","value":7.5 ,"unit":"mg/dL","reference_range":"20 - 40","status":"CRITICAL LOW"},
    {"parameter":"Serum Copper","value":35.0 ,"unit":"ug/dL","reference_range":"70 - 140","status":"CRITICAL LOW"},
    {"parameter":"24h Urinary Copper","value":240.0 ,"unit":"ug/24h","reference_range":"15 - 50","status":"CRITICAL HIGH"}
    ],
    "metadata":{
    "patient_id":"PERSIST-001",
    "patient_name":"Persistence Test Patient",
    "age":30 ,
    "gender":"Male",
    "report_id":"REP-PERSIST-001",
    "report_date":"2026-08-27"
    },
    "filename":"PERSIST_001_Report.txt",
    "file_type":"TXT"
    }
    status ,anl1_res =make_req ("/api/analyzer/analyze",method ="POST",data =analyzer_payload_1 ,token =admin_token )
    assert status ==200 ,f"Analysis failed: {anl1_res }"
    print (f"[STEP 3] Generated AI Report for PERSIST-001: Analysis ID {anl1_res ['analysis_id']}, Report ID {anl1_res .get ('report_id')}")


    analyzer_payload_2 ={
    "parameters":[
    {"parameter":"TSH","value":32.5 ,"unit":"uIU/mL","reference_range":"0.4 - 4.2","status":"CRITICAL HIGH"},
    {"parameter":"T4","value":2.1 ,"unit":"ug/dL","reference_range":"4.5 - 12.0","status":"LOW"},
    {"parameter":"T3","value":0.6 ,"unit":"ng/dL","reference_range":"0.8 - 2.0","status":"LOW"}
    ],
    "metadata":{
    "patient_id":"PERSIST-002",
    "patient_name":"Second Persistence Patient",
    "age":45 ,
    "gender":"Female",
    "report_id":"REP-PERSIST-002",
    "report_date":"2026-08-27"
    },
    "patient_meta":{
    "patient_id":"PERSIST-002",
    "name":"Second Persistence Patient",
    "age":45 ,
    "gender":"Female"
    },
    "filename":"PERSIST_002_Thyroid.txt",
    "file_type":"TXT"
    }
    status ,anl2_res =make_req ("/api/analyzer/analyze",method ="POST",data =analyzer_payload_2 ,token =admin_token )
    assert status ==200 ,f"Analysis for PERSIST-002 failed: {anl2_res }"
    print (f"[STEP 4] Auto-registered & Generated Report for PERSIST-002: Analysis ID {anl2_res ['analysis_id']}")


    print ("\n[STEP 5] Simulating Full Page Refresh / Backend Querying...")


    status ,public_pats =make_req ("/api/patients/public")
    assert status ==200 
    pids =[p ["patient_id"]for p in public_pats ]
    assert "PERSIST-001"in pids ,"PERSIST-001 missing from public directory!"
    assert "PERSIST-002"in pids ,"PERSIST-002 missing from public directory!"
    assert "PAT-1001"in pids ,"Sample demo patient PAT-1001 was overwritten!"
    print (f"  [PASS] Public directory returned {len (public_pats )} patients (including PERSIST-001, PERSIST-002, and Demo patients).")


    status ,admin_pats =make_req ("/api/patients",token =admin_token )
    assert status ==200 
    admin_pids =[p ["patient_id"]for p in admin_pats ]
    assert "PERSIST-001"in admin_pids 
    assert "PERSIST-002"in admin_pids 
    print (f"  [PASS] Admin patient directory returned {len (admin_pats )} verified database records.")


    status ,admin_reps =make_req ("/api/reports",token =admin_token )
    assert status ==200 
    rep_pids =[r ["patient_id"]for r in admin_reps ]
    assert "PERSIST-001"in rep_pids 
    assert "PERSIST-002"in rep_pids 
    print (f"  [PASS] Admin reports directory returned {len (admin_reps )} reports (including PERSIST-001 & PERSIST-002).")


    print ("\n[STEP 6] Testing Patient Portal Logins & Isolation...")

    status ,p1_auth =make_req ("/api/patient/login",method ="POST",data ={"patient_id":"PERSIST-001","access_pin":"PIN-001"})
    assert status ==200 ,f"PERSIST-001 login failed: {p1_auth }"
    p1_token =p1_auth ["token"]
    status ,p1_reports =make_req (f"/api/reports?patient_id=PERSIST-001",token =p1_token )
    assert status ==200 
    for r in p1_reports :
        assert r ["patient_id"]=="PERSIST-001","Data leak: PERSIST-001 received non-owned report!"
    print (f"  [PASS] PERSIST-001 authenticated and retrieved {len (p1_reports )} reports isolated strictly to PERSIST-001.")


    status ,p2_auth =make_req ("/api/patient/login",method ="POST",data ={"patient_id":"PERSIST-002","access_pin":"PIN-002"})
    assert status ==200 ,f"PERSIST-002 login failed: {p2_auth }"
    p2_token =p2_auth ["token"]
    status ,p2_reports =make_req (f"/api/reports?patient_id=PERSIST-002",token =p2_token )
    assert status ==200 
    for r in p2_reports :
        assert r ["patient_id"]=="PERSIST-002","Data leak: PERSIST-002 received non-owned report!"
    print (f"  [PASS] PERSIST-002 authenticated and retrieved {len (p2_reports )} reports isolated strictly to PERSIST-002.")


    print ("\n[STEP 7] Direct SQLite File Inspection...")
    conn =sqlite3 .connect (DB_PATH )
    conn .row_factory =sqlite3 .Row 
    c =conn .cursor ()

    c .execute ("SELECT patient_id, name, age, gender FROM patients WHERE patient_id IN ('PERSIST-001', 'PERSIST-002')")
    db_pats =c .fetchall ()
    assert len (db_pats )==2 ,f"Expected 2 persistence patients in SQLite, found {len (db_pats )}"
    print (f"  [PASS] SQLite 'patients' table has: {[dict (r )for r in db_pats ]}")

    c .execute ("SELECT report_id, patient_id, test_category, status FROM lab_reports WHERE patient_id IN ('PERSIST-001', 'PERSIST-002')")
    db_reps =c .fetchall ()
    assert len (db_reps )>=2 ,f"Expected at least 2 reports in SQLite, found {len (db_reps )}"
    print (f"  [PASS] SQLite 'lab_reports' table has: {[dict (r )for r in db_reps ]}")

    c .execute ("SELECT analysis_id, patient_id, source_filename FROM report_analyses WHERE patient_id IN ('PERSIST-001', 'PERSIST-002')")
    db_analyses =c .fetchall ()
    assert len (db_analyses )>=2 ,f"Expected at least 2 analyses in SQLite, found {len (db_analyses )}"
    print (f"  [PASS] SQLite 'report_analyses' table has: {[dict (r )for r in db_analyses ]}")
    conn .close ()

    print ("\n"+"="*80 )
    print ("  [SUCCESS] ALL PATIENT & REPORT PERSISTENCE CHECKS PASSED 100%")
    print ("="*80 )

if __name__ =="__main__":
    test_persistence_flow ()
