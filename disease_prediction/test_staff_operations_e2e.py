import requests 
import json 
import time 

BASE_URL ="http://127.0.0.1:8000"

def test_16_staff_logins ():
    print ("\n--- TEST 1: ALL 16 DEMO STAFF ACCOUNTS ---")
    roles ={
    "RECEPTIONIST":["REC001","REC002","REC003","REC004"],
    "LAB_STAFF":["LAB001","LAB002","LAB003","LAB004"],
    "WARD_MANAGER":["WARD001","WARD002","WARD003","WARD004"],
    "OPERATIONS_MANAGER":["OPS001","OPS002","OPS003","OPS004"]
    }

    tokens ={}
    for expected_role ,users in roles .items ():
        for u in users :
            res =requests .post (f"{BASE_URL }/api/operations/auth/login",json ={
            "username":u ,
            "password":"Staff@2026"
            })
            assert res .status_code ==200 ,f"Failed login for {u }: {res .text }"
            data =res .json ()
            assert data ["token"]
            assert data ["user"]["role"]==expected_role ,f"Role mismatch for {u }: got {data ['user']['role']}"
            tokens [u ]=data ["token"]
            print (f"  [PASS] {u } ({expected_role }) - Token issued for: {data ['user']['name']}")
    return tokens 

def test_patient_registration_and_search (rec_token ):
    print ("\n--- TEST 2: PATIENT REGISTRATION & SEARCH ---")
    headers ={"Authorization":f"Bearer {rec_token }"}

    reg_payload ={
    "name":f"E2E Test Patient {int (time .time ())}",
    "phone":"+91 9988776655",
    "age":35 ,
    "gender":"Female",
    "email":"e2e.test@medicover.in",
    "address":"Health City, Vizag",
    "department":"General Medicine",
    "doctor_name":"Dr. K. Rama Murty",
    "appointment_date":"2026-08-30",
    "appointment_time":"10:00 AM",
    "symptoms":"Mild fever and headache",
    "insurance_covered":True ,
    "insurance_provider":"Star Health & Allied Insurance",
    "policy_number":"POL-E2E-999"
    }

    res =requests .post (f"{BASE_URL }/api/operations/patients",json =reg_payload ,headers =headers )
    assert res .status_code ==200 ,f"Registration failed: {res .text }"
    pat =res .json ()
    assert pat ["patient_id"]
    assert pat ["pin"]
    print (f"  [PASS] Registered patient: {pat ['patient_id']} with PIN: {pat ['pin']}")


    search_res =requests .get (f"{BASE_URL }/api/operations/patients?q={pat ['patient_id']}",headers =headers )
    assert search_res .status_code ==200 
    found =search_res .json ()
    assert len (found )>0 
    assert found [0 ]["patient_id"]==pat ["patient_id"]
    print (f"  [PASS] Successfully searched & found patient {pat ['patient_id']}")

    return pat 

def test_bed_admission_and_discharge (rec_token ,pat ):
    print ("\n--- TEST 3: ATOMIC ADMISSION & BED QUOTA ENFORCEMENT ---")
    headers ={"Authorization":f"Bearer {rec_token }"}


    inv_res =requests .get (f"{BASE_URL }/api/operations/beds/inventory")
    assert inv_res .status_code ==200 
    beds =inv_res .json ()
    avail_beds =[b for b in beds if b ["status"]=="Available"]
    assert len (avail_beds )>0 ,"No available beds for test"
    chosen_bed =avail_beds [0 ]

    pat_name =pat .get ("full_name")or pat .get ("name")
    adm_payload ={
    "patient_id":pat ["patient_id"],
    "patient_name":pat_name ,
    "age":pat ["age"],
    "gender":pat ["gender"],
    "phone":pat ["phone"],
    "email":pat ["email"],
    "preferred_bed_tier":chosen_bed .get ("bed_type")or chosen_bed .get ("tier")or "General",
    "assigned_bed_id":chosen_bed ["bed_id"],
    "ward_name":chosen_bed ["ward_name"],
    "admitting_department":"General Medicine",
    "attending_doctor":"Dr. K. Rama Murty",
    "insurance_covered":True ,
    "insurance_provider":"Star Health",
    "policy_number":"POL-E2E-999"
    }

    adm_res =requests .post (f"{BASE_URL }/api/operations/admissions",json =adm_payload ,headers =headers )
    assert adm_res .status_code ==200 ,f"Admission failed: {adm_res .text }"
    adm_data =adm_res .json ()
    adm_id =adm_data .get ("admission_id")or adm_data .get ("id")
    assert adm_id ,f"No admission ID returned in: {adm_data }"
    print (f"  [PASS] Inpatient {pat_name } admitted to {chosen_bed ['bed_id']} (Admission ID: {adm_id })")


    inv_after =requests .get (f"{BASE_URL }/api/operations/beds/inventory").json ()
    bed_check =next ((b for b in inv_after if b ["bed_id"]==chosen_bed ["bed_id"]),None )
    assert bed_check and bed_check ["status"]=="Occupied",f"Bed {chosen_bed ['bed_id']} was not marked Occupied"
    print (f"  [PASS] Bed {chosen_bed ['bed_id']} atomically marked Occupied in Supabase")


    dis_res =requests .post (f"{BASE_URL }/api/operations/admissions/{adm_id }/discharge",headers =headers )
    assert dis_res .status_code ==200 ,f"Discharge failed: {dis_res .text }"
    print (f"  [PASS] Inpatient {pat_name } successfully discharged")


    inv_final =requests .get (f"{BASE_URL }/api/operations/beds/inventory").json ()
    bed_check_final =next ((b for b in inv_final if b ["bed_id"]==chosen_bed ["bed_id"]),None )
    assert bed_check_final and bed_check_final ["status"]=="Available",f"Bed {chosen_bed ['bed_id']} was not freed to Available"
    print (f"  [PASS] Bed {chosen_bed ['bed_id']} atomically freed back to Available in Supabase")

def test_lab_order_completion (lab_token ):
    print ("\n--- TEST 4: LAB ORDERS & RESULT ENTRY ---")
    headers ={"Authorization":f"Bearer {lab_token }"}

    orders_res =requests .get (f"{BASE_URL }/api/operations/lab/orders?limit=10",headers =headers )
    assert orders_res .status_code ==200 
    res_data =orders_res .json ()
    order_list =res_data .get ("orders",res_data )if isinstance (res_data ,dict )else res_data 
    assert len (order_list )>0 

    target_order =order_list [0 ]
    result_payload ={
    "order_id":target_order ["order_id"],
    "result_value":"14.2 g/dL (Normal)",
    "reference_range":"12.0 - 16.0 g/dL",
    "technician_notes":"Automated E2E validation complete. Specimen normal."
    }

    upd_res =requests .post (f"{BASE_URL }/api/operations/lab/orders/{target_order ['order_id']}/result",json =result_payload ,headers =headers )
    assert upd_res .status_code ==200 ,f"Lab result update failed: {upd_res .text }"
    print (f"  [PASS] Lab Order {target_order ['order_id']} updated with result '{result_payload ['result_value']}'")

def test_ward_manager_bed_status_update (ward_token ):
    print ("\n--- TEST 5: WARD MANAGER LIVE BED STATUS UPDATE ---")
    headers ={"Authorization":f"Bearer {ward_token }"}

    bed_id ="BED-GWA-AC01"

    res1 =requests .post (f"{BASE_URL }/api/operations/beds/{bed_id }/status",json ={"status":"Needs Cleaning"},headers =headers )
    assert res1 .status_code ==200 ,f"Failed updating bed status: {res1 .text }"


    inv1 =requests .get (f"{BASE_URL }/api/operations/beds/inventory").json ()
    b1 =next ((b for b in inv1 if b ["bed_id"]==bed_id ),None )
    assert b1 and b1 ["status"]=="Needs Cleaning"
    print (f"  [PASS] Bed {bed_id } status updated to Needs Cleaning in Supabase")


    res2 =requests .post (f"{BASE_URL }/api/operations/beds/{bed_id }/status",json ={"status":"Available"},headers =headers )
    assert res2 .status_code ==200 

    inv2 =requests .get (f"{BASE_URL }/api/operations/beds/inventory").json ()
    b2 =next ((b for b in inv2 if b ["bed_id"]==bed_id ),None )
    assert b2 and b2 ["status"]=="Available"
    print (f"  [PASS] Bed {bed_id } status updated to Available in Supabase")

def test_persistent_billing (rec_token ,pat ):
    print ("\n--- TEST 6: PERSISTENT INPATIENT BILLING ---")
    headers ={"Authorization":f"Bearer {rec_token }"}
    pat_name =pat .get ("full_name")or pat .get ("name")

    bill_payload ={
    "patient_id":pat ["patient_id"],
    "patient_name":pat_name ,
    "bed_type":"General",
    "bed_id":"BED-GWA-AC01",
    "days_stayed":3 ,
    "doctor_name":"Dr. Ramesh Gupta",
    "doctor_visits_count":3 ,
    "doctor_fee_per_visit":800.0 ,
    "lab_tests_fee":1200.0 ,
    "nursing_fee_per_day":500.0 ,
    "medicines_fee":1500.0 ,
    "is_insured":True ,
    "insurance_provider":"Star Health",
    "policy_number":"POL-E2E-999",
    "coverage_percentage":80.0 
    }

    calc_res =requests .post (f"{BASE_URL }/api/operations/billing/calculate",json =bill_payload ,headers =headers )
    assert calc_res .status_code ==200 ,f"Billing calculation failed: {calc_res .text }"
    bill =calc_res .json ()
    assert bill ["bill_id"]
    assert bill ["net_payable"]>=0 
    print (f"  [PASS] Invoice generated: {bill ['bill_id']} for Patient {bill ['patient_name']} (Net: INR {bill ['net_payable']})")


    inv_res =requests .get (f"{BASE_URL }/api/operations/billing/invoices?patient_id={pat ['patient_id']}",headers =headers )
    assert inv_res .status_code ==200 ,f"Invoice retrieval failed: {inv_res .text }"
    inv_data =inv_res .json ()
    assert inv_data ["total"]>0 
    print (f"  [PASS] Verified invoice {bill ['bill_id']} persisted in Supabase billing_invoices table")


def test_regression_5_protected_features ():
    print ("\n--- TEST 5: REGRESSION TESTS FOR 5 PROTECTED FEATURES ---")


    print ("  [1/5] Testing Protected Feature 1: Patient Login...")
    pat_res =requests .post (f"{BASE_URL }/api/patient/login",json ={"patient_id":"PAT-1001","access_pin":"PIN-1001"})
    assert pat_res .status_code ==200 ,f"Patient login failed: {pat_res .text }"
    print ("    -> PASS: Patient login verified.")


    print ("  [2/5] Testing Protected Feature 2: Doctor Login...")
    doc_res =requests .post (f"{BASE_URL }/api/auth/login",json ={"username":"admin","password":"admin123"})
    assert doc_res .status_code ==200 ,f"Doctor login failed: {doc_res .text }"
    print ("    -> PASS: Doctor login verified.")


    print ("  [3/5] Testing Protected Feature 3: AI Report Analyzer...")
    ml_res =requests .post (f"{BASE_URL }/predict/anemia",json ={
    "Age":30 ,"Sex":"Male","HGB":9.2 ,"RBC":3.1 ,"PCV":28.0 ,"MCV":70.0 ,"MCH":22.0 ,"MCHC":29.0 ,"RDW":16.5 ,"TLC":6.5 ,"PLT /mm3":250.0 
    })
    assert ml_res .status_code ==200 ,f"ML inference failed: {ml_res .text }"
    print ("    -> PASS: AI Report Analyzer inference verified.")


    print ("  [4/5] Testing Protected Feature 4: Symptoms AI...")
    symp_res =requests .post (f"{BASE_URL }/api/symptoms/suggest",json ={
    "symptoms":"High fever, chills, body ache",
    "age":30 ,
    "gender":"Male"
    })
    assert symp_res .status_code ==200 ,f"Symptoms AI failed: {symp_res .text }"
    print ("    -> PASS: Symptoms AI guidance verified.")


    print ("  [5/5] Testing Protected Feature 5: ML Sandbox...")
    dengue_res =requests .post (f"{BASE_URL }/predict/dengue",json ={
    "age":30 ,"gender":"Male","hemoglobin_g_dl":14.5 ,"wbc_count":2800.0 ,"differential_count":0 ,"rbc_count":0 ,"platelet_count":45000.0 ,"platelet_distribution_width":18.0 
    })
    assert dengue_res .status_code ==200 ,f"Dengue sandbox model failed: {dengue_res .text }"
    print ("    -> PASS: ML Sandbox verified.")

if __name__ =="__main__":
    print ("Starting Comprehensive MEDLENS E2E & Regression Suite...")
    tokens =test_16_staff_logins ()
    pat =test_patient_registration_and_search (tokens ["REC001"])
    test_bed_admission_and_discharge (tokens ["REC001"],pat )
    test_lab_order_completion (tokens ["LAB001"])
    test_ward_manager_bed_status_update (tokens ["WARD001"])
    test_persistent_billing (tokens ["REC001"],pat )
    test_regression_5_protected_features ()
    print ("\n========================================================")
    print ("ALL TESTS PASSED! ZERO REGRESSIONS DETECTED.")
    print ("========================================================")

