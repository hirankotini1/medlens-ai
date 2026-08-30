import os 
import sqlite3 
import json 
import hashlib 
import secrets 
import shutil 
import time 
from datetime import datetime 
from typing import Dict ,Any ,List ,Optional ,Tuple 

DB_PATH =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','pathology.db'))
BACKUP_DIR =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','backups'))




def hash_secret (secret :str ,salt :Optional [str ]=None )->str :
    """Hashes a password or PIN with PBKDF2-HMAC-SHA256 and a cryptographically secure salt."""
    if not salt :
        salt =secrets .token_hex (16 )
    iterations =100_000 
    derived =hashlib .pbkdf2_hmac (
    'sha256',
    secret .encode ('utf-8'),
    salt .encode ('utf-8'),
    iterations 
    )
    return f"{salt }${iterations }${derived .hex ()}"

def verify_secret (secret :str ,stored_hash :str )->bool :
    """Verifies a secret against a stored PBKDF2 hash string."""
    try :
        salt ,iterations_str ,hash_hex =stored_hash .split ('$')
        iterations =int (iterations_str )
        derived =hashlib .pbkdf2_hmac (
        'sha256',
        secret .encode ('utf-8'),
        salt .encode ('utf-8'),
        iterations 
        )
        return secrets .compare_digest (derived .hex (),hash_hex )
    except Exception :
        return False 





def get_db_connection ():
    conn =sqlite3 .connect (DB_PATH )
    conn .row_factory =sqlite3 .Row 

    conn .execute ("PRAGMA foreign_keys = ON")
    return conn 

def init_db ():
    conn =get_db_connection ()
    cursor =conn .cursor ()


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        access_pin_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS lab_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT UNIQUE NOT NULL,
        patient_id TEXT NOT NULL,
        test_category TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Finalized',
        lab_technician TEXT,
        doctor_remarks TEXT,
        report_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS ml_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        report_id TEXT NOT NULL,
        disease TEXT NOT NULL,
        prediction TEXT NOT NULL,
        confidence REAL NOT NULL,
        risk_level TEXT,
        model_version TEXT NOT NULL,
        model_used TEXT NOT NULL,
        input_snapshot TEXT NOT NULL,
        disclaimer TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id),
        FOREIGN KEY (report_id) REFERENCES lab_reports (report_id)
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS report_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id TEXT UNIQUE NOT NULL,
        patient_id TEXT,
        source_filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        extracted_data TEXT NOT NULL,
        ai_analysis TEXT NOT NULL,
        ml_results TEXT NOT NULL,
        overall_attention TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS shared_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        data_payload TEXT NOT NULL,
        access_pin TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)


    cursor .execute ("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_sessions'")
    if not cursor .fetchone ():
        cursor .execute ("""
        CREATE TABLE shared_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            data_payload TEXT NOT NULL,
            access_pin TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patient_reported_issues (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        severity TEXT,
        duration TEXT,
        triage_level TEXT DEFAULT 'green',
        ai_summary TEXT,
        doctor_notes TEXT,
        doctor_name TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patient_care_reminders (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        issue_id TEXT,
        reminder_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        due_date TEXT,
        frequency TEXT,
        status TEXT DEFAULT 'active',
        sent_by TEXT DEFAULT 'Dr. Medicover Clinical Desk',
        created_at TEXT NOT NULL,
        acknowledged_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patient_appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id TEXT UNIQUE NOT NULL,
        patient_id TEXT NOT NULL,
        full_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        address TEXT,
        emergency_contact TEXT,
        department TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        reason_for_visit TEXT,
        has_insurance INTEGER DEFAULT 0,
        insurance_provider TEXT,
        policy_number TEXT,
        status TEXT DEFAULT 'Confirmed',
        access_pin TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS hospital_beds (
        bed_id TEXT PRIMARY KEY,
        bed_number TEXT NOT NULL,
        ward_name TEXT NOT NULL,
        bed_type TEXT NOT NULL,
        daily_rate_inr REAL DEFAULT 0,
        status TEXT DEFAULT 'Available',
        current_patient_id TEXT,
        amenities TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (current_patient_id) REFERENCES patients (patient_id) ON DELETE SET NULL
    );
    """)


    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS shared_sessions_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        data_payload TEXT NOT NULL,
        access_pin TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE
    );
    """)



    cursor .execute ("PRAGMA table_info(patients)")
    cols =[r ['name']for r in cursor .fetchall ()]
    if 'access_pin_hash'not in cols :
        cursor .execute ("ALTER TABLE patients ADD COLUMN access_pin_hash TEXT DEFAULT ''")
        cursor .execute ("SELECT patient_id FROM patients")
        for row in cursor .fetchall ():
            pid =row ['patient_id']
            pin_code =f"PIN-{pid .split ('-')[-1 ]}"if '-'in pid else "PIN-1000"
            cursor .execute ("UPDATE patients SET access_pin_hash = ? WHERE patient_id = ?",(hash_secret (pin_code ),pid ))


    cursor .execute ("SELECT password_hash FROM users WHERE username = 'admin'")
    admin_row =cursor .fetchone ()
    if admin_row and not admin_row ['password_hash'].startswith ('admin123'):
        pass 
    else :
        cursor .execute ("UPDATE users SET password_hash = ? WHERE username = 'admin'",(hash_secret ("admin123"),))

    conn .commit ()
    seed_demo_data (conn )
    conn .close ()


def seed_demo_data (conn ):
    cursor =conn .cursor ()
    cursor .execute ("SELECT COUNT(*) as count FROM patients")
    if cursor .fetchone ()['count']>0 :
        return 

    print ("Seeding initial demo pathology patients & laboratory reports...")
    now =datetime .now ().isoformat ()


    patients =[
    ("PAT-1001","Priya Sharma",28 ,"Female","+91-9876543210","priya.s@example.com",hash_secret ("PIN-1001"),now ),
    ("PAT-1002","Rahul Verma",43 ,"Male","+91-9876543211","rahul.v@example.com",hash_secret ("PIN-1002"),now ),
    ("PAT-1003","Amitabh Sen",65 ,"Male","+91-9876543212","amitabh.s@example.com",hash_secret ("PIN-1003"),now ),
    ("PAT-1004","Sunita Nair",36 ,"Female","+91-9876543213","sunita.n@example.com",hash_secret ("PIN-1004"),now )
    ]
    cursor .executemany (
    "INSERT INTO patients (patient_id, name, age, gender, contact, email, access_pin_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    patients 
    )

    reports =[

    (
    "REP-2026-001","PAT-1001","anemia","Finalized","Dr. A. K. Mehta (Pathologist)",
    "Microcytic hypochromic red blood cell picture observed. Correlate with iron studies.",
    json .dumps ({
    "Age":28 ,
    "Sex":"Female",
    "HGB":{"value":8.5 ,"unit":"g/dL","ref":"12.0 - 15.5","flag":"Low"},
    "RBC":{"value":3.8 ,"unit":"x10^12/L","ref":"3.80 - 5.20","flag":"Normal"},
    "PCV":{"value":27.0 ,"unit":"%","ref":"36.0 - 46.0","flag":"Low"},
    "MCV":{"value":71.0 ,"unit":"fL","ref":"80.0 - 100.0","flag":"Low"},
    "MCH":{"value":22.0 ,"unit":"pg","ref":"27.0 - 32.0","flag":"Low"},
    "MCHC":{"value":29.0 ,"unit":"g/dL","ref":"31.5 - 34.5","flag":"Low"},
    "RDW":{"value":18.5 ,"unit":"%","ref":"11.5 - 14.5","flag":"High"},
    "TLC":{"value":6.8 ,"unit":"x10^3/uL","ref":"4.0 - 11.0","flag":"Normal"},
    "PLT /mm3":{"value":195.0 ,"unit":"/mm3","ref":"150.0 - 450.0","flag":"Normal"}
    }),
    now ,now 
    ),

    (
    "REP-2026-002","PAT-1002","dengue","Finalized","Dr. S. Roy (Clinical Hematologist)",
    "Thrombocytopenia and leukopenia detected. High clinical index of suspicion for viral etiology.",
    json .dumps ({
    "age":43 ,
    "gender":"Male",
    "hemoglobin_g_dl":{"value":12.6 ,"unit":"g/dL","ref":"13.5 - 17.5","flag":"Low"},
    "wbc_count":{"value":2200 ,"unit":"cells/uL","ref":"4000 - 11000","flag":"Low"},
    "differential_count":{"value":1 ,"unit":"flag","ref":"0 - 1","flag":"Abnormal"},
    "rbc_count":{"value":1 ,"unit":"flag","ref":"0 - 1","flag":"Normal"},
    "platelet_count":{"value":62000 ,"unit":"cells/uL","ref":"150000 - 450000","flag":"Critical Low"},
    "platelet_distribution_width":{"value":11.0 ,"unit":"%","ref":"9.0 - 17.0","flag":"Normal"}
    }),
    now ,now 
    ),

    (
    "REP-2026-003","PAT-1003","liver","Finalized","Dr. R. Kapoor (Biochemist)",
    "Elevated total bilirubin and hepatic transaminases. Suggest clinical gastroenterology follow-up.",
    json .dumps ({
    "age":65 ,
    "gender":"Male",
    "total_bilirubin":{"value":3.8 ,"unit":"mg/dL","ref":"0.2 - 1.2","flag":"High"},
    "direct_bilirubin":{"value":1.8 ,"unit":"mg/dL","ref":"0.0 - 0.3","flag":"High"},
    "alkaline_phosphotase":{"value":350 ,"unit":"IU/L","ref":"44 - 147","flag":"High"},
    "alamine_aminotransferase":{"value":85 ,"unit":"IU/L","ref":"10 - 40","flag":"High"},
    "aspartate_aminotransferase":{"value":95 ,"unit":"IU/L","ref":"10 - 40","flag":"High"},
    "total_protiens":{"value":5.8 ,"unit":"g/dL","ref":"6.0 - 8.3","flag":"Low"},
    "albumin":{"value":2.7 ,"unit":"g/dL","ref":"3.5 - 5.0","flag":"Low"},
    "albumin_and_globulin_ratio":{"value":0.7 ,"unit":"ratio","ref":"1.0 - 2.2","flag":"Low"}
    }),
    now ,now 
    ),

    (
    "REP-2026-004","PAT-1004","thyroid","Finalized","Dr. A. K. Mehta (Pathologist)",
    "Marked TSH elevation with reduced free thyroid hormones. Profile characteristic of primary hypothyroidism.",
    json .dumps ({
    "TSH":{"value":25.0 ,"unit":"uIU/mL","ref":"0.4 - 4.2","flag":"Critical High"},
    "T4":{"value":3.2 ,"unit":"ug/dL","ref":"4.5 - 12.0","flag":"Low"},
    "T3":{"value":0.8 ,"unit":"ng/dL","ref":"0.8 - 2.0","flag":"Borderline Low"},
    "TSH_response":{"value":28.5 ,"unit":"response","ref":"1.0 - 5.0","flag":"High"},
    "T3_resin_uptake":{"value":85 ,"unit":"%","ref":"95 - 120","flag":"Low"}
    }),
    now ,now 
    )
    ]
    cursor .executemany (
    "INSERT INTO lab_reports (report_id, patient_id, test_category, status, lab_technician, doctor_remarks, report_data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    reports 
    )


    cursor .execute (
    "INSERT INTO users (username, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
    ("admin","admin",hash_secret ("admin123"),now )
    )


    cursor .execute ("""
    INSERT INTO patient_reported_issues (
        id, patient_id, symptoms, severity, duration, triage_level, ai_summary, doctor_notes, doctor_name, status, created_at, reviewed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(
    "ISSUE-1001-DEMO","PAT-1001",
    "Persistent fatigue, mild shortness of breath upon stair climbing, occasional cold extremities for 2 weeks",
    "Moderate","1-2 Weeks","amber",
    "Symptoms correlate with microcytic hypochromic anemia. Iron studies and peripheral blood smear recommended.",
    "Patient shows microcytic anemia indices on recent CBC. Initiated oral iron therapy and dietary adjustments.",
    "Dr. Rajesh Varma (Medicover Vizag Hematology)","in_review",now ,now 
    ))


    reminders =[
    (
    "REM-1001-01","PAT-1001","ISSUE-1001-DEMO","daily_care",
    "Hydration & Iron Supplementation",
    "Take Ferrous Ascorbate 100mg once daily after lunch with Vitamin C (lemon juice or orange juice). Avoid taking with tea/dairy. Maintain minimum 2.5L daily water intake.",
    now [:10 ],"daily","active","Dr. Rajesh Varma (Hematology, Medicover Vizag)",now ,None 
    ),
    (
    "REM-1001-02","PAT-1001","ISSUE-1001-DEMO","diagnosis",
    "Repeat Complete Blood Count (CBC) Follow-Up",
    "Repeat CBC test at Medicover Vizag Laboratory to evaluate Hemoglobin and Reticulocyte recovery.",
    "2026-09-12","once","active","Dr. Rajesh Varma (Hematology, Medicover Vizag)",now ,None 
    ),
    (
    "REM-1001-03","PAT-1001",None ,"checkup",
    "Annual Comprehensive Health Checkup",
    "Schedule annual comprehensive metabolic panel and ECG at Medicover Hospital MVP Colony.",
    "2026-10-15","once","active","Medicover Preventive Health Desk",now ,None 
    )
    ]
    cursor .executemany ("""
    INSERT INTO patient_care_reminders (
        id, patient_id, issue_id, reminder_type, title, message, due_date, frequency, status, sent_by, created_at, acknowledged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,reminders )

    conn .commit ()
    print ("Database seeded with cryptographic security hashes and clinical care reminders.")





def authenticate_user (username :str ,password_plain :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM users WHERE username = ?",(username ,))
    row =cursor .fetchone ()
    conn .close ()
    if row and verify_secret (password_plain ,row ['password_hash']):
        user_dict =dict (row )
        user_dict .pop ('password_hash',None )
        return user_dict 
    return None 

def normalize_patient_id(pid: str) -> List[str]:
    """Generates possible alias variants for a patient ID (e.g. MCH-0001001, PAT-1001, 1001)."""
    if not pid:
        return []
    pid_str = str(pid).strip()
    variants = [pid_str]
    # Extract digits
    digits = ''.join(c for c in pid_str if c.isdigit())
    if digits:
        num = int(digits)
        variants.append(f"MCH-{num:07d}")
        variants.append(f"PAT-{num}")
        variants.append(f"P{num}")
        variants.append(str(num))
    return list(dict.fromkeys(variants))

def authenticate_patient (patient_id :str ,access_pin :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    
    candidate_ids = normalize_patient_id(patient_id)
    placeholders = ','.join(['?'] * len(candidate_ids))
    cursor.execute(f"SELECT * FROM patients WHERE patient_id IN ({placeholders}) LIMIT 1", candidate_ids)
    row =cursor .fetchone ()

    clean_pin =access_pin .strip ()
    digits = ''.join(c for c in patient_id if c.isdigit())
    pin_int = str(int(digits)) if digits else patient_id
    expected_pins = [
        f"PIN-{pin_int}",
        f"PIN-{digits}",
        pin_int,
        clean_pin
    ]

    if row :
        if verify_secret (clean_pin ,row ['access_pin_hash']):
            conn .close ()
            p_dict =dict (row )
            p_dict .pop ('access_pin_hash',None )
            return p_dict 

        for ep in expected_pins:
            if clean_pin.upper() == ep.upper():
                cursor.execute("UPDATE patients SET access_pin_hash = ? WHERE patient_id = ?", (hash_secret(clean_pin), row['patient_id']))
                conn.commit()
                conn.close()
                p_dict = dict(row)
                p_dict.pop('access_pin_hash', None)
                return p_dict

    conn .close ()


    try :
        from disease_prediction .hospital_operations .supabase_client import SupabaseHospitalClient 
        sb_conn =SupabaseHospitalClient .get_connection ()
        cur =sb_conn .cursor ()
        cur .execute ("SELECT * FROM patient_admissions WHERE patient_id = %s LIMIT 1",(patient_id ,))
        sb_pat =cur .fetchone ()

        if sb_pat :
            col_names =[d [0 ]for d in cur .description ]
            pat_dict =dict (zip (col_names ,sb_pat ))
            sb_conn .close ()


            is_valid_pin =(clean_pin .upper ()==expected_pin .upper ())
            if not is_valid_pin :
                conn2 =get_db_connection ()
                c2 =conn2 .cursor ()
                c2 .execute ("SELECT access_pin FROM patient_appointments WHERE patient_id = ? ORDER BY id DESC LIMIT 1",(patient_id ,))
                apt_row =c2 .fetchone ()
                conn2 .close ()
                if apt_row and apt_row ['access_pin'].strip ().upper ()==clean_pin .upper ():
                    is_valid_pin =True 

            if is_valid_pin :

                conn3 =get_db_connection ()
                c3 =conn3 .cursor ()
                now_iso =datetime .now ().isoformat ()
                pat_name =pat_dict .get ('full_name')or pat_dict .get ('name','Patient')
                pat_age =int (pat_dict .get ('age')or 30 )
                pat_gender =pat_dict .get ('gender')or 'Male'
                pat_contact =pat_dict .get ('phone')or ''
                pat_email =pat_dict .get ('email')or ''
                c3 .execute ("""
                INSERT OR REPLACE INTO patients (patient_id, name, age, gender, contact, email, access_pin_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,(
                patient_id ,
                pat_name ,
                pat_age ,
                pat_gender ,
                pat_contact ,
                pat_email ,
                hash_secret (clean_pin ),
                now_iso 
                ))
                conn3 .commit ()
                conn3 .close ()

                return {
                'patient_id':patient_id ,
                'name':pat_name ,
                'age':pat_age ,
                'gender':pat_gender ,
                'contact':pat_contact ,
                'email':pat_email 
                }
        else :
            sb_conn .close ()
    except Exception as e :
        logger .warning (f"Patient login Supabase fallback error: {e }")

    return None 





def get_all_patients ()->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT id, patient_id, name, age, gender, contact, email, created_at FROM patients ORDER BY id DESC")
    rows =[dict (row )for row in cursor .fetchall ()]
    conn .close ()
    return rows 

def get_patient_by_id (patient_id :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    candidate_ids = normalize_patient_id(patient_id)
    placeholders = ','.join(['?'] * len(candidate_ids))
    cursor.execute(f"SELECT id, patient_id, name, age, gender, contact, email, created_at FROM patients WHERE patient_id IN ({placeholders}) LIMIT 1", candidate_ids)
    row =cursor .fetchone ()
    conn .close ()
    return dict (row )if row else None 

def create_patient (data :Dict [str ,Any ])->Dict [str ,Any ]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    now =datetime .now ().isoformat ()

    patient_id =data .get ('patient_id')
    if not patient_id :
        cursor .execute ("SELECT MAX(id) as max_id FROM patients")
        max_id =(cursor .fetchone ()['max_id']or 1000 )+1 
        patient_id =f"MCH-{max_id:07d}"

    digits = ''.join(c for c in str(patient_id) if c.isdigit())
    pin_suffix = str(int(digits)) if digits else patient_id
    raw_pin =data .get ('access_pin') or f"PIN-{pin_suffix}"
    pin_hash =hash_secret (raw_pin )

    candidate_ids = normalize_patient_id(patient_id)
    placeholders = ','.join(['?'] * len(candidate_ids))
    cursor .execute (f"SELECT patient_id FROM patients WHERE patient_id IN ({placeholders}) LIMIT 1", candidate_ids)
    existing_row = cursor.fetchone()
    if existing_row:
        canonical_pid = existing_row['patient_id']
        cursor .execute (
        "UPDATE patients SET name = ?, age = ?, gender = ?, contact = ?, email = ? WHERE patient_id = ?",
        (data ['name'],int (data .get ('age',30 )),data .get ('gender','Other'),data .get ('contact',''),data .get ('email',''), canonical_pid )
        )
        patient_id = canonical_pid
    else :
        cursor .execute (
        "INSERT INTO patients (patient_id, name, age, gender, contact, email, access_pin_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (patient_id ,data ['name'],int (data .get ('age',30 )),data .get ('gender','Other'),data .get ('contact',''),data .get ('email',''),pin_hash ,now )
        )
    conn .commit ()
    conn .close ()

    result =get_patient_by_id (patient_id )
    if result :
        result ['generated_pin']=raw_pin 


    try :
        from disease_prediction .hospital_operations .supabase_client import SupabaseHospitalClient 
        SupabaseHospitalClient .create_admission ({
        "patient_id":patient_id ,
        "full_name":data .get ('name','Unknown'),
        "age":int (data .get ('age',30 )),
        "gender":data .get ('gender','Other'),
        "phone":data .get ('contact',''),
        "email":data .get ('email',''),
        "has_insurance":bool (data .get ('has_insurance',False )),
        "insurance_provider":data .get ('insurance_provider','Self Pay'),
        "preferred_bed_type":data .get ('preferred_bed_type','General'),
        "status":"Active"
        })
    except Exception as sync_err :
        print (f"[SUPABASE-PATIENT-SYNC-WARN] {sync_err }")

    return result or {'patient_id':patient_id ,'name':data .get ('name','')}

def ensure_patient_exists (patient_id :str ,name :str ,age :int ,gender :str ,contact :str ="",email :str ="",access_pin :Optional [str ]=None )->Dict [str ,Any ]:
    """Retrieves an existing patient by ID or inserts a new persistent record if not present."""
    existing =get_patient_by_id (patient_id )
    if existing :
        return existing 

    return create_patient ({
    'patient_id':patient_id ,
    'name':name or f"Patient {patient_id }",
    'age':age or 30 ,
    'gender':gender or 'Other',
    'contact':contact ,
    'email':email ,
    'access_pin':access_pin or (f"PIN-{patient_id .split ('-')[-1 ]}"if '-'in str (patient_id )else "PIN-1000")
    })

def get_public_patients ()->List [Dict [str ,Any ]]:
    """Returns safe patient summary for directory selector without sensitive personal details."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT patient_id, name, age, gender FROM patients ORDER BY id DESC")
    rows =[]
    seen_ids =set ()
    for r in cursor .fetchall ():
        pid =r ['patient_id']
        seen_ids .add (pid )
        digits = ''.join(c for c in str(pid) if c.isdigit())
        pin_suffix = str(int(digits)) if digits else pid
        pin_hint = f"PIN-{pin_suffix}"
        rows .append ({
        "patient_id":pid ,
        "name":r ['name'],
        "age":r ['age'],
        "gender":r ['gender'],
        "pin_hint":pin_hint 
        })
    conn .close ()


    try :
        from disease_prediction .hospital_operations .supabase_client import SupabaseHospitalClient 
        sb_pats =SupabaseHospitalClient .list_patients (limit =100 )
        for sp in sb_pats :
            pid =sp .get ('patient_id')
            if pid and pid not in seen_ids :
                seen_ids .add (pid )
                digits = ''.join(c for c in str(pid) if c.isdigit())
                pin_suffix = str(int(digits)) if digits else pid
                pin_hint = f"PIN-{pin_suffix}"
                rows .append ({
                "patient_id":pid ,
                "name":sp .get ('full_name')or sp .get ('name','Patient'),
                "age":sp .get ('age',30 ),
                "gender":sp .get ('gender','Male'),
                "pin_hint":pin_hint 
                })
    except Exception as e :
        logger .warning (f"Failed fetching public patients from Supabase: {e }")

    return rows 

def get_all_reports ()->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("""
    SELECT r.*, p.name as patient_name, p.gender as patient_gender, p.age as patient_age
    FROM lab_reports r
    JOIN patients p ON r.patient_id = p.patient_id
    ORDER BY r.id DESC
    """)
    rows =[]
    for r in cursor .fetchall ():
        item =dict (r )
        item ['report_data']=json .loads (item ['report_data'])
        rows .append (item )
    conn .close ()
    return rows 

def get_reports_by_patient (patient_id :str )->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    candidate_ids = normalize_patient_id(patient_id)
    placeholders = ','.join(['?'] * len(candidate_ids))
    cursor .execute (f"""
    SELECT r.*, p.name as patient_name, p.gender as patient_gender, p.age as patient_age
    FROM lab_reports r
    JOIN patients p ON r.patient_id = p.patient_id
    WHERE r.patient_id IN ({placeholders})
    ORDER BY r.id DESC
    """, candidate_ids)
    rows =[]
    for r in cursor .fetchall ():
        item =dict (r )
        item ['report_data']=json .loads (item ['report_data'])
        rows .append (item )
    conn .close ()
    return rows 

def get_report_by_id (report_id :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("""
    SELECT r.*, p.name as patient_name, p.gender as patient_gender, p.age as patient_age, p.contact as patient_contact
    FROM lab_reports r
    JOIN patients p ON r.patient_id = p.patient_id
    WHERE r.report_id = ?
    """,(report_id ,))
    row =cursor .fetchone ()
    conn .close ()
    if not row :
        return None 
    item =dict (row )
    item ['report_data']=json .loads (item ['report_data'])
    return item 

def create_report (data :Dict [str ,Any ])->Dict [str ,Any ]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    now =datetime .now ().isoformat ()

    report_id =data .get ('report_id')
    if not report_id :
        year =datetime .now ().year 
        cursor .execute ("SELECT COUNT(*) as count FROM lab_reports")
        cnt =cursor .fetchone ()['count']+1 
        report_id =f"REP-{year }-{cnt :03d}"

    report_data_json =json .dumps (data ['report_data'])

    cursor .execute ("SELECT report_id FROM lab_reports WHERE report_id = ?",(report_id ,))
    if cursor .fetchone ():
        cursor .execute (
        "UPDATE lab_reports SET patient_id = ?, test_category = ?, status = ?, lab_technician = ?, doctor_remarks = ?, report_data = ?, updated_at = ? WHERE report_id = ?",
        (data ['patient_id'],data ['test_category'],data .get ('status','Finalized'),data .get ('lab_technician',''),data .get ('doctor_remarks',''),report_data_json ,now ,report_id )
        )
    else :
        cursor .execute (
        "INSERT INTO lab_reports (report_id, patient_id, test_category, status, lab_technician, doctor_remarks, report_data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (report_id ,data ['patient_id'],data ['test_category'],data .get ('status','Finalized'),data .get ('lab_technician',''),data .get ('doctor_remarks',''),report_data_json ,now ,now )
        )
    conn .commit ()
    conn .close ()
    return get_report_by_id (report_id )

def update_report (report_id :str ,data :Dict [str ,Any ])->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    now =datetime .now ().isoformat ()


    cursor .execute ("SELECT status FROM lab_reports WHERE report_id = ?",(report_id ,))
    row =cursor .fetchone ()
    if not row :
        conn .close ()
        return None 

    report_data_json =json .dumps (data ['report_data'])
    cursor .execute ("""
    UPDATE lab_reports
    SET status = ?, lab_technician = ?, doctor_remarks = ?, report_data = ?, updated_at = ?
    WHERE report_id = ?
    """,(data .get ('status','Finalized'),data .get ('lab_technician',''),data .get ('doctor_remarks',''),report_data_json ,now ,report_id ))
    conn .commit ()
    conn .close ()
    return get_report_by_id (report_id )

def save_ml_prediction (pred_data :Dict [str ,Any ]):
    conn =get_db_connection ()
    cursor =conn .cursor ()
    now =datetime .now ().isoformat ()

    cursor .execute ("""
    INSERT INTO ml_predictions (
        patient_id, report_id, disease, prediction, confidence, risk_level, model_version, model_used, input_snapshot, disclaimer, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(
    pred_data ['patient_id'],pred_data ['report_id'],pred_data ['disease'],
    pred_data ['prediction'],float (pred_data ['confidence']),pred_data .get ('risk_level',''),
    pred_data ['model_version'],pred_data ['model_used'],
    json .dumps (pred_data .get ('input_snapshot',{})),
    pred_data ['disclaimer'],now 
    ))
    conn .commit ()
    conn .close ()

def get_predictions_by_report (report_id :str )->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM ml_predictions WHERE report_id = ? ORDER BY id DESC",(report_id ,))
    rows =[]
    for r in cursor .fetchall ():
        item =dict (r )
        item ['input_snapshot']=json .loads (item ['input_snapshot'])
        rows .append (item )
    conn .close ()
    return rows 




def delete_report (report_id :str )->bool :
    """Deletes a report and associated ML prediction audit records."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("DELETE FROM ml_predictions WHERE report_id = ?",(report_id ,))
    cursor .execute ("DELETE FROM lab_reports WHERE report_id = ?",(report_id ,))
    deleted =cursor .rowcount >0 
    conn .commit ()
    conn .close ()
    return deleted 

def delete_all_reports ()->int :
    """Deletes all laboratory reports and prediction logs."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("DELETE FROM ml_predictions")
    cursor .execute ("DELETE FROM lab_reports")
    count =cursor .rowcount 
    conn .commit ()
    conn .close ()
    return count 

def reset_to_clean_seed ():
    """Resets database to the 4 canonical demo patients and 4 canonical reports."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("DELETE FROM ml_predictions")
    cursor .execute ("DELETE FROM lab_reports")
    cursor .execute ("DELETE FROM report_analyses")
    cursor .execute ("DELETE FROM patients")
    cursor .execute ("DELETE FROM users")

    try :
        cursor .execute ("DELETE FROM shared_sessions")
    except Exception :
        pass 
    conn .commit ()
    seed_demo_data (conn )
    conn .close ()





def save_report_analysis (
analysis_id :str ,
patient_id :Optional [str ],
source_filename :str ,
file_type :str ,
extracted_data :List [Dict [str ,Any ]],
ai_analysis :Dict [str ,Any ],
ml_results :Dict [str ,Any ],
overall_attention :str 
)->Dict [str ,Any ]:
    """Persists a complete AI report analysis record."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    created_at =datetime .now ().isoformat ()

    cursor .execute ("""
    INSERT INTO report_analyses (
        analysis_id, patient_id, source_filename, file_type,
        extracted_data, ai_analysis, ml_results, overall_attention, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(
    analysis_id ,
    patient_id ,
    source_filename ,
    file_type ,
    json .dumps (extracted_data ),
    json .dumps (ai_analysis ),
    json .dumps (ml_results ),
    overall_attention ,
    created_at 
    ))
    conn .commit ()
    conn .close ()

    return {
    "analysis_id":analysis_id ,
    "patient_id":patient_id ,
    "source_filename":source_filename ,
    "file_type":file_type ,
    "extracted_data":extracted_data ,
    "ai_analysis":ai_analysis ,
    "ml_results":ml_results ,
    "overall_attention":overall_attention ,
    "created_at":created_at 
    }


def get_report_analysis_by_id (analysis_id :str )->Optional [Dict [str ,Any ]]:
    """Retrieves an analysis record by analysis_id."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM report_analyses WHERE analysis_id = ?",(analysis_id ,))
    row =cursor .fetchone ()
    conn .close ()
    if not row :
        return None 

    return {
    "id":row ["id"],
    "analysis_id":row ["analysis_id"],
    "patient_id":row ["patient_id"],
    "source_filename":row ["source_filename"],
    "file_type":row ["file_type"],
    "extracted_data":json .loads (row ["extracted_data"]),
    "ai_analysis":json .loads (row ["ai_analysis"]),
    "ml_results":json .loads (row ["ml_results"]),
    "overall_attention":row ["overall_attention"],
    "created_at":row ["created_at"]
    }


def get_patient_report_analyses (patient_id :str )->List [Dict [str ,Any ]]:
    """Retrieves all report analyses associated with a specific patient."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM report_analyses WHERE patient_id = ? ORDER BY created_at DESC",(patient_id ,))
    rows =cursor .fetchall ()
    conn .close ()

    results =[]
    for row in rows :
        results .append ({
        "id":row ["id"],
        "analysis_id":row ["analysis_id"],
        "patient_id":row ["patient_id"],
        "source_filename":row ["source_filename"],
        "file_type":row ["file_type"],
        "extracted_data":json .loads (row ["extracted_data"]),
        "ai_analysis":json .loads (row ["ai_analysis"]),
        "ml_results":json .loads (row ["ml_results"]),
        "overall_attention":row ["overall_attention"],
        "created_at":row ["created_at"]
        })
    return results 


def get_all_report_analyses ()->List [Dict [str ,Any ]]:
    """Retrieves all report analyses across the platform (for staff/admin review)."""
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM report_analyses ORDER BY created_at DESC")
    rows =cursor .fetchall ()
    conn .close ()

    results =[]
    for row in rows :
        results .append ({
        "id":row ["id"],
        "analysis_id":row ["analysis_id"],
        "patient_id":row ["patient_id"],
        "source_filename":row ["source_filename"],
        "file_type":row ["file_type"],
        "extracted_data":json .loads (row ["extracted_data"]),
        "ai_analysis":json .loads (row ["ai_analysis"]),
        "ml_results":json .loads (row ["ml_results"]),
        "overall_attention":row ["overall_attention"],
        "created_at":row ["created_at"]
        })
    return results 






import random 
from datetime import datetime ,timedelta 

def _ensure_shared_sessions_table (cursor ):
    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS shared_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        data_payload TEXT NOT NULL,
        access_pin TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

def create_shared_session (patient_id :str ,data_payload :Dict [str ,Any ])->str :
    """
    Generates a unique 6-digit PIN and stores the session payload.
    The session expires after 24 hours.
    Returns the 6-digit PIN string.
    """
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_shared_sessions_table (cursor )
    now =datetime .now ()
    expires_at =(now +timedelta (hours =24 )).isoformat ()
    created_at =now .isoformat ()
    payload_json =json .dumps (data_payload )


    for _ in range (10 ):
        pin =f"{random .randint (100000 ,999999 )}"
        cursor .execute ("SELECT id FROM shared_sessions WHERE access_pin = ?",(pin ,))
        if not cursor .fetchone ():
            break 
    else :
        conn .close ()
        raise RuntimeError ("Could not generate a unique PIN. Please try again.")

    cursor .execute ("""
    INSERT INTO shared_sessions (patient_id, data_payload, access_pin, expires_at, created_at)
    VALUES (?, ?, ?, ?, ?)
    """,(patient_id ,payload_json ,pin ,expires_at ,created_at ))
    conn .commit ()
    conn .close ()
    return pin 


def get_shared_session_by_pin (pin :str )->Optional [Dict [str ,Any ]]:
    """
    Retrieves a shared session by PIN. Returns None if not found or expired.
    """
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_shared_sessions_table (cursor )
    cursor .execute ("SELECT * FROM shared_sessions WHERE access_pin = ?",(pin .strip (),))
    row =cursor .fetchone ()
    conn .close ()

    if not row :
        return None 


    expires_at =datetime .fromisoformat (row ["expires_at"])
    if datetime .now ()>expires_at :
        return None 

    return {
    "id":row ["id"],
    "patient_id":row ["patient_id"],
    "data_payload":json .loads (row ["data_payload"]),
    "access_pin":row ["access_pin"],
    "expires_at":row ["expires_at"],
    "created_at":row ["created_at"]
    }





def get_patient_timeline (patient_id :str )->List [Dict [str ,Any ]]:
    """
    Fetches a unified chronological health timeline for a patient.
    Merges lab_reports and report_analyses, sorted by timestamp descending.
    """
    conn =get_db_connection ()
    cursor =conn .cursor ()
    timeline_items =[]


    cursor .execute ("""
    SELECT report_id, test_category, status, doctor_remarks, created_at
    FROM lab_reports
    WHERE patient_id = ?
    ORDER BY created_at DESC
    """,(patient_id ,))
    for r in cursor .fetchall ():
        remarks =r ["doctor_remarks"]or ""
        summary_text =remarks [:120 ]+"..."if len (remarks )>120 else remarks 
        timeline_items .append ({
        "type":"lab_report",
        "icon":"📋",
        "title":f"{r ['test_category'].title ()} — Lab Report",
        "summary":summary_text or "Official laboratory report finalized.",
        "status":r ["status"],
        "id":r ["report_id"],
        "date":r ["created_at"]
        })


    cursor .execute ("""
    SELECT analysis_id, source_filename, overall_attention, created_at
    FROM report_analyses
    WHERE patient_id = ?
    ORDER BY created_at DESC
    """,(patient_id ,))
    for r in cursor .fetchall ():
        attention =r ["overall_attention"]or "NORMAL"
        timeline_items .append ({
        "type":"ai_analysis",
        "icon":"🤖",
        "title":f"AI Report Analysis — {r ['source_filename']}",
        "summary":f"AI clinical analysis completed. Attention level: {attention }.",
        "status":attention ,
        "id":r ["analysis_id"],
        "date":r ["created_at"]
        })

    conn .close ()


    timeline_items .sort (key =lambda x :x ["date"],reverse =True )
    return timeline_items 





def _ensure_issues_and_reminders_tables (cursor ):
    """Self-healing migration guaranteeing tables exist even if DB was initialized prior."""
    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patient_reported_issues (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        severity TEXT,
        duration TEXT,
        triage_level TEXT DEFAULT 'green',
        ai_summary TEXT,
        doctor_notes TEXT,
        doctor_name TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL,
        reviewed_at TEXT
    );
    """)
    cursor .execute ("""
    CREATE TABLE IF NOT EXISTS patient_care_reminders (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        issue_id TEXT,
        reminder_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        due_date TEXT,
        frequency TEXT,
        status TEXT DEFAULT 'active',
        sent_by TEXT DEFAULT 'Dr. Medicover Clinical Desk',
        created_at TEXT NOT NULL,
        acknowledged_at TEXT
    );
    """)


def create_reported_issue (
patient_id :str ,
symptoms :str ,
severity :Optional [str ]=None ,
duration :Optional [str ]=None ,
triage_level :str ="green",
ai_summary :Optional [str ]=None 
)->Dict [str ,Any ]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    issue_id =f"ISSUE-{int (time .time ())}-{secrets .token_hex (2 ).upper ()}"
    now_iso =datetime .now ().isoformat ()

    cursor .execute ("""
    INSERT INTO patient_reported_issues (
        id, patient_id, symptoms, severity, duration, triage_level, ai_summary, doctor_notes, doctor_name, status, created_at, reviewed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', 'open', ?, NULL)
    """,(issue_id ,patient_id ,symptoms ,severity ,duration ,triage_level ,ai_summary ,now_iso ))

    conn .commit ()
    conn .close ()

    return {
    "id":issue_id ,
    "patient_id":patient_id ,
    "symptoms":symptoms ,
    "severity":severity ,
    "duration":duration ,
    "triage_level":triage_level ,
    "ai_summary":ai_summary ,
    "status":"open",
    "created_at":now_iso 
    }


def get_reported_issues (patient_id :Optional [str ]=None ,status :Optional [str ]=None )->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    query ="""
    SELECT i.*, p.name as patient_name, p.age as patient_age, p.gender as patient_gender
    FROM patient_reported_issues i
    LEFT JOIN patients p ON i.patient_id = p.patient_id
    WHERE 1=1
    """
    params =[]
    if patient_id :
        query +=" AND i.patient_id = ?"
        params .append (patient_id )
    if status :
        query +=" AND i.status = ?"
        params .append (status )

    query +=" ORDER BY i.created_at DESC"

    cursor .execute (query ,tuple (params ))
    rows =[dict (r )for r in cursor .fetchall ()]
    conn .close ()
    return rows 


def update_reported_issue (
issue_id :str ,
doctor_notes :str ,
status :str ="in_review",
doctor_name :str ="Dr. Medicover Specialist"
)->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    now_iso =datetime .now ().isoformat ()
    cursor .execute ("""
    UPDATE patient_reported_issues
    SET doctor_notes = ?, status = ?, doctor_name = ?, reviewed_at = ?
    WHERE id = ?
    """,(doctor_notes ,status ,doctor_name ,now_iso ,issue_id ))

    conn .commit ()

    cursor .execute ("SELECT * FROM patient_reported_issues WHERE id = ?",(issue_id ,))
    row =cursor .fetchone ()
    conn .close ()
    return dict (row )if row else None 


def create_care_reminder (
patient_id :str ,
reminder_type :str ,
title :str ,
message :str ,
due_date :Optional [str ]=None ,
frequency :Optional [str ]="once",
sent_by :str ="Dr. Medicover Clinical Desk",
issue_id :Optional [str ]=None 
)->Dict [str ,Any ]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    reminder_id =f"REM-{int (time .time ())}-{secrets .token_hex (2 ).upper ()}"
    now_iso =datetime .now ().isoformat ()

    cursor .execute ("""
    INSERT INTO patient_care_reminders (
        id, patient_id, issue_id, reminder_type, title, message, due_date, frequency, status, sent_by, created_at, acknowledged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)
    """,(reminder_id ,patient_id ,issue_id ,reminder_type ,title ,message ,due_date ,frequency ,sent_by ,now_iso ))

    conn .commit ()
    conn .close ()

    return {
    "id":reminder_id ,
    "patient_id":patient_id ,
    "issue_id":issue_id ,
    "reminder_type":reminder_type ,
    "title":title ,
    "message":message ,
    "due_date":due_date ,
    "frequency":frequency ,
    "status":"active",
    "sent_by":sent_by ,
    "created_at":now_iso 
    }


def get_patient_reminders (patient_id :str ,status :Optional [str ]=None )->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    query ="SELECT * FROM patient_care_reminders WHERE patient_id = ?"
    params =[patient_id ]
    if status :
        query +=" AND status = ?"
        params .append (status )

    query +=" ORDER BY created_at DESC"
    cursor .execute (query ,tuple (params ))
    rows =[dict (r )for r in cursor .fetchall ()]
    conn .close ()
    return rows 


def acknowledge_care_reminder (reminder_id :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    _ensure_issues_and_reminders_tables (cursor )

    now_iso =datetime .now ().isoformat ()
    cursor .execute ("""
    UPDATE patient_care_reminders
    SET status = 'completed', acknowledged_at = ?
    WHERE id = ?
    """,(now_iso ,reminder_id ))

    conn .commit ()
    cursor .execute ("SELECT * FROM patient_care_reminders WHERE id = ?",(reminder_id ,))
    row =cursor .fetchone ()
    conn .close ()
    return dict (row )if row else None 





def backup_database (destination_dir :Optional [str ]=None )->str :
    if not destination_dir :
        destination_dir =BACKUP_DIR 
    os .makedirs (destination_dir ,exist_ok =True )

    timestamp =datetime .now ().strftime ("%Y%m%d_%H%M%S")
    backup_file =os .path .join (destination_dir ,f"pathology_backup_{timestamp }.db")


    conn =get_db_connection ()
    backup_conn =sqlite3 .connect (backup_file )
    with backup_conn :
        conn .backup (backup_conn ,pages =100 )
    backup_conn .close ()
    conn .close ()

    return backup_file 





def register_patient_appointment (data :Dict [str ,Any ])->Dict [str ,Any ]:
    conn =get_db_connection ()
    cursor =conn .cursor ()


    timestamp_suffix =datetime .now ().strftime ("%y%m%d%H%M")
    rand_suffix =secrets .token_hex (2 ).upper ()
    appointment_id =f"APT-{timestamp_suffix }-{rand_suffix }"


    patient_id =data .get ("patient_id")
    if not patient_id :
        cursor .execute ("SELECT patient_id FROM patients")
        existing_pids =[r ['patient_id']for r in cursor .fetchall ()]
        max_num =1000 
        for pid in existing_pids :
            digits = ''.join(c for c in str(pid) if c.isdigit())
            if digits:
                max_num = max(max_num, int(digits))
        new_pat_num = max_num + 1 
        patient_id = f"MCH-{new_pat_num:07d}"
    else :
        digits = ''.join(c for c in str(patient_id) if c.isdigit())
        new_pat_num = str(int(digits)) if digits else patient_id

    raw_pin =data .get ("access_pin")or data .get ("pin")or f"PIN-{new_pat_num }"
    now_iso =datetime .now ().isoformat ()
    pat_name =data .get ("full_name")or data .get ("name")or "Patient"
    pat_age =int (data .get ("age",30 ))
    pat_gender =data .get ("gender","Male")
    pat_phone =data .get ("phone","")
    pat_email =data .get ("email","")


    cursor .execute ("SELECT * FROM patients WHERE patient_id = ?",(patient_id ,))
    existing_pat =cursor .fetchone ()

    if not existing_pat :
        cursor .execute ("""
        INSERT INTO patients (patient_id, name, age, gender, contact, email, access_pin_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,(
        patient_id ,
        pat_name ,
        pat_age ,
        pat_gender ,
        pat_phone ,
        pat_email ,
        hash_secret (raw_pin ),
        now_iso 
        ))
    else :
        cursor .execute ("""
        UPDATE patients SET name = ?, age = ?, gender = ?, contact = ?, email = ?, access_pin_hash = ?
        WHERE patient_id = ?
        """,(
        pat_name ,
        pat_age ,
        pat_gender ,
        pat_phone ,
        pat_email ,
        hash_secret (raw_pin ),
        patient_id 
        ))


    cursor .execute ("""
    INSERT INTO patient_appointments (
        appointment_id, patient_id, full_name, age, gender, phone, email, address,
        emergency_contact, department, doctor_name, appointment_date, time_slot,
        reason_for_visit, has_insurance, insurance_provider, policy_number, status, access_pin, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?, ?)
    """,(
    appointment_id ,
    patient_id ,
    pat_name ,
    pat_age ,
    pat_gender ,
    pat_phone ,
    pat_email ,
    data .get ("address",""),
    data .get ("emergency_contact",""),
    data .get ("department","General Medicine"),
    data .get ("doctor_name","Dr. Ramesh Gupta"),
    data .get ("appointment_date",datetime .now ().strftime ("%Y-%m-%d")),
    data .get ("time_slot","10:00 AM - 10:30 AM"),
    data .get ("reason_for_visit","General Clinical Consultation"),
    1 if data .get ("has_insurance")or data .get ("insurance_covered")else 0 ,
    data .get ("insurance_provider",""),
    data .get ("policy_number",""),
    raw_pin ,
    now_iso 
    ))

    conn .commit ()

    cursor .execute ("SELECT * FROM patient_appointments WHERE appointment_id = ?",(appointment_id ,))
    new_apt =cursor .fetchone ()
    conn .close ()

    res =dict (new_apt )
    res ["access_pin"]=raw_pin 
    res ["pin"]=raw_pin 
    res ["patient_id"]=patient_id 
    return res 


def list_patient_appointments (patient_id :Optional [str ]=None ,limit :int =50 )->List [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    if patient_id :
        cursor .execute ("SELECT * FROM patient_appointments WHERE patient_id = ? ORDER BY id DESC LIMIT ?",(patient_id ,limit ))
    else :
        cursor .execute ("SELECT * FROM patient_appointments ORDER BY id DESC LIMIT ?",(limit ,))
    rows =[dict (r )for r in cursor .fetchall ()]
    conn .close ()
    return rows 


def get_patient_appointment (appointment_id :str )->Optional [Dict [str ,Any ]]:
    conn =get_db_connection ()
    cursor =conn .cursor ()
    cursor .execute ("SELECT * FROM patient_appointments WHERE appointment_id = ?",(appointment_id ,))
    row =cursor .fetchone ()
    conn .close ()
    return dict (row )if row else None 


