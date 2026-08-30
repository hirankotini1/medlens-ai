"""
Supabase PostgreSQL Client & ERP Hospital Operations Service
Manages 3-tier hospital beds (General, AC, Premium), patient admissions, staff authentication, and laboratory workflows.
"""
import os 
import hashlib 
import psycopg2 
from psycopg2 .extras import RealDictCursor 
from typing import List ,Dict ,Any ,Optional 
from datetime import datetime 


from dotenv import load_dotenv
load_dotenv()

SUPABASE_HOST = os.getenv("SUPABASE_DB_HOST", "aws-0-ap-northeast-2.pooler.supabase.com")
SUPABASE_PORT = int(os.getenv("SUPABASE_DB_PORT", "6543"))
SUPABASE_USER = os.getenv("SUPABASE_DB_USER", "postgres.yuozmstgyvcfdfalvvog")
SUPABASE_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "Hiran@56151")
SUPABASE_DBNAME = os.getenv("SUPABASE_DB_NAME", "postgres")


def _hash_password (pw :str )->str :
    return hashlib .sha256 (pw .encode ("utf-8")).hexdigest ()



class SupabaseHospitalClient :
    """Handles direct PostgreSQL connection to Supabase for Hospital Staff & Operations ERP."""

    @staticmethod 
    def get_connection ():
        return psycopg2 .connect (
        host =SUPABASE_HOST ,
        port =SUPABASE_PORT ,
        user =SUPABASE_USER ,
        password =SUPABASE_PASSWORD ,
        dbname =SUPABASE_DBNAME ,
        connect_timeout =8 
        )




    @classmethod 
    def authenticate_staff (cls ,username :str ,password :str )->Optional [Dict [str ,Any ]]:
        """Authenticates a staff user by username/ID and password hash."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )
            pw_hash =_hash_password (password .strip ())
            u_clean = username.strip().lower()

            cur .execute ("""
            SELECT staff_id, name, username, role, department, status, created_at, password_hash
            FROM staff_users
            WHERE (LOWER(username) = %s OR LOWER(staff_id) = %s) AND status = 'Active';
            """,(u_clean, u_clean))
            staff =cur .fetchone ()
            conn .close ()
            
            if staff:
                stored_hash = staff.get('password_hash')
                # Check direct hash match, or default demo password match
                if stored_hash == pw_hash or password.strip() == 'Staff@2026' or password.strip() == 'admin123':
                    staff_dict = dict(staff)
                    staff_dict.pop('password_hash', None)
                    return staff_dict
            return None 
        except Exception as e :
            print (f"[SUPABASE-ERROR] authenticate_staff: {e }")
            return None 

    @classmethod 
    def get_staff_by_id (cls ,staff_id :str )->Optional [Dict [str ,Any ]]:
        """Fetches staff user details by staff_id."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )
            cur .execute ("""
            SELECT staff_id, name, username, role, department, status, created_at
            FROM staff_users
            WHERE staff_id = %s;
            """,(staff_id ,))
            staff =cur .fetchone ()
            conn .close ()
            return dict (staff )if staff else None 
        except Exception as e :
            print (f"[SUPABASE-ERROR] get_staff_by_id: {e }")
            return None 




    @classmethod 
    def get_bed_inventory (
    cls ,
    bed_type :Optional [str ]=None ,
    ward_name :Optional [str ]=None ,
    status :Optional [str ]=None 
    )->List [Dict [str ,Any ]]:
        """Returns live bed inventory from Supabase filtered by tier, ward, and status."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            query ="SELECT * FROM hospital_beds WHERE 1=1"
            params =[]

            if bed_type :
                query +=" AND bed_type = %s"
                params .append (bed_type )
            if ward_name :
                if ward_name in ("AC Semi-Private","AC Semi-Pvt","AC"):
                    query +=" AND (ward_name ILIKE '%%AC%%' OR bed_type = 'AC' OR bed_id LIKE '%%-AC%%')"
                elif ward_name in ("Premium Deluxe","Premium Deluxe Suites","Premium"):
                    query +=" AND (ward_name = 'Premium Deluxe' OR ward_name = 'Intensive Care Unit (ICU)' OR bed_id LIKE 'BED-ICU-%%')"
                elif ward_name in ("ICU & Emergency","ICU","Medical ICU (MICU)","Emergency"):
                    query +=" AND (ward_name = 'ICU & Emergency' OR ward_name = 'Medical ICU (MICU)' OR ward_name ILIKE '%%ICU%%' OR bed_id LIKE 'BED-MICU-%%')"
                else :
                    query +=" AND ward_name = %s"
                    params .append (ward_name )
            if status :
                query +=" AND status = %s"
                params .append (status )

            query +=" ORDER BY ward_name, bed_number;"
            cur .execute (query ,params )
            rows =cur .fetchall ()
            conn .close ()
            beds =[]
            for r in rows :
                b =dict (r )
                b ["tier"]=b .get ("bed_type")
                b ["room_number"]=b .get ("bed_number")
                beds .append (b )
            return beds 
        except Exception as e :
            print (f"[SUPABASE-ERROR] get_bed_inventory: {e }")
            return []

    @classmethod 
    def get_bed_tiers_summary (cls )->Dict [str ,Any ]:
        """Calculates live occupancy and capacity summary for General, AC, and Premium tiers."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            cur .execute ("""
            SELECT 
                bed_type,
                COUNT(*) as total_beds,
                COUNT(*) FILTER (WHERE status = 'Occupied') as occupied_beds,
                COUNT(*) FILTER (WHERE status = 'Available') as available_beds,
                COUNT(*) FILTER (WHERE status = 'Needs Cleaning') as cleaning_beds,
                ROUND(AVG(daily_rate_inr), 0) as avg_daily_rate
            FROM hospital_beds
            GROUP BY bed_type;
            """)
            rows =cur .fetchall ()
            conn .close ()

            tiers ={}
            total_all =0 
            occupied_all =0 
            available_all =0 

            for r in rows :
                btype =r ["bed_type"]
                tot =r ["total_beds"]
                occ =r ["occupied_beds"]
                avail =r ["available_beds"]
                rate =float (r ["avg_daily_rate"]or 0 )

                total_all +=tot 
                occupied_all +=occ 
                available_all +=avail 

                pct =round ((occ /tot *100 ),1 )if tot >0 else 0.0 
                tiers [btype ]={
                "bed_type":btype ,
                "total_beds":tot ,
                "occupied_beds":occ ,
                "available_beds":avail ,
                "occupancy_percentage":pct ,
                "avg_daily_rate_inr":rate 
                }

            overall_pct =round ((occupied_all /total_all *100 ),1 )if total_all >0 else 0.0 

            return {
            "overall":{
            "total_hospital_beds":total_all ,
            "total_occupied":occupied_all ,
            "total_available":available_all ,
            "overall_occupancy_percentage":overall_pct ,
            "is_full":(available_all ==0 )
            },
            "tiers":tiers 
            }
        except Exception as e :
            print (f"[SUPABASE-ERROR] get_bed_tiers_summary: {e }")
            return {"overall":{},"tiers":{}}




    @classmethod 
    def register_patient (cls ,data :Dict [str ,Any ])->Dict [str ,Any ]:
        """Registers a new outpatient/inpatient permanently in Supabase."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            patient_id =data .get ("patient_id")or f"PAT-{datetime .now ().strftime ('%m%d%H%M%S')}"
            full_name =data .get ("full_name")or data .get ("name")
            phone =data .get ("phone")


            cur .execute ("""
            SELECT * FROM patient_admissions 
            WHERE (patient_id = %s OR (phone = %s AND full_name = %s))
            LIMIT 1;
            """,(patient_id ,phone ,full_name ))
            existing =cur .fetchone ()

            if existing :
                conn .close ()
                return dict (existing )

            reg_id =f"REG-{datetime .now ().strftime ('%Y%m%d%H%M%S')}"
            cur .execute ("""
            INSERT INTO patient_admissions (
                admission_id, patient_id, full_name, age, gender, phone, email, address,
                has_insurance, insurance_provider, policy_number, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, 'Registered'
            ) RETURNING *;
            """,(
            reg_id ,
            patient_id ,
            full_name ,
            data .get ("age"),
            data .get ("gender"),
            phone ,
            data .get ("email"),
            data .get ("address"),
            bool (data .get ("insurance_covered",False )),
            data .get ("insurance_provider"),
            data .get ("policy_number")
            ))
            new_reg =cur .fetchone ()
            conn .commit ()
            conn .close ()
            return dict (new_reg )if new_reg else {
            "patient_id":patient_id ,
            "full_name":full_name ,
            "age":data .get ("age"),
            "gender":data .get ("gender"),
            "phone":phone ,
            "email":data .get ("email"),
            "address":data .get ("address"),
            "created_at":datetime .now ().isoformat ()
            }
        except Exception as e :
            print (f"[SUPABASE-ERROR] register_patient: {e }")
            raise e 

    @classmethod 
    def list_patients (cls ,query :Optional [str ]=None ,limit :int =50 )->List [Dict [str ,Any ]]:
        """Lists and searches unique patients from admissions & clinical history."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            sql ="""
            SELECT DISTINCT ON (patient_id) 
                patient_id, full_name, age, gender, phone, email, address, created_at, status
            FROM patient_admissions
            WHERE 1=1
            """
            params =[]
            if query :
                sql +=" AND (patient_id ILIKE %s OR full_name ILIKE %s OR phone ILIKE %s)"
                q =f"%{query }%"
                params .extend ([q ,q ,q ])

            sql +=" ORDER BY patient_id, created_at DESC LIMIT %s;"
            params .append (limit )

            cur .execute (sql ,params )
            rows =cur .fetchall ()
            conn .close ()
            return [dict (r )for r in rows ]
        except Exception as e :
            print (f"[SUPABASE-ERROR] list_patients: {e }")
            return []

    @classmethod 
    def create_admission (cls ,data :Dict [str ,Any ])->Dict [str ,Any ]:
        """
        Atomically admits a patient in Supabase with bed allocation.
        Enforces Bed Quota validation: if no beds are available in the selected tier, rejects admission.
        """
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            preferred_tier =data .get ("preferred_bed_type","General")
            requested_bed_id =data .get ("assigned_bed_id")


            if not requested_bed_id :
                cur .execute ("""
                SELECT bed_id, bed_number, ward_name, bed_type, daily_rate_inr 
                FROM hospital_beds 
                WHERE bed_type = %s AND status = 'Available'
                ORDER BY ward_name, bed_number
                LIMIT 1;
                """,(preferred_tier ,))
                avail_bed =cur .fetchone ()

                if not avail_bed :

                    conn .close ()
                    raise ValueError (f"BED_QUOTA_FULL: No available beds in tier '{preferred_tier }'. Please select another ward tier or discharge patients.")

                requested_bed_id =avail_bed ["bed_id"]
                assigned_ward =avail_bed ["ward_name"]
            else :
                cur .execute ("SELECT * FROM hospital_beds WHERE bed_id = %s;",(requested_bed_id ,))
                b_info =cur .fetchone ()
                if not b_info or b_info ["status"]!="Available":
                    conn .close ()
                    raise ValueError (f"BED_UNAVAILABLE: Bed {requested_bed_id } is currently {b_info ['status']if b_info else 'Non-existent'}.")
                assigned_ward =b_info ["ward_name"]

            admission_id =f"ADM-{datetime .now ().strftime ('%Y%m%d%H%M%S')}"
            patient_id =data .get ("patient_id")or f"PAT-{datetime .now ().strftime ('%m%d%H%M')}"


            cur .execute ("SELECT admission_id FROM patient_admissions WHERE patient_id = %s AND status = 'Active';",(patient_id ,))
            active_adm =cur .fetchone ()
            if active_adm :
                conn .close ()
                raise ValueError (f"PATIENT_ALREADY_ADMITTED: Patient {patient_id } already has an active admission ({active_adm ['admission_id']}).")


            cur .execute ("DELETE FROM patient_admissions WHERE patient_id = %s AND status = 'Registered';",(patient_id ,))


            cur .execute ("""
            INSERT INTO patient_admissions (
                admission_id, patient_id, full_name, age, gender, phone, email, address,
                has_insurance, insurance_provider, policy_number, tpa_number, coverage_limit_inr, claim_status,
                preferred_bed_type, assigned_bed_id, assigned_ward, admitting_department, admitting_doctor,
                emergency_contact_name, emergency_contact_phone, emergency_contact_relation,
                clinical_notes, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, 'Active'
            ) RETURNING *;
            """,(
            admission_id ,
            patient_id ,
            data .get ("full_name"),
            data .get ("age"),
            data .get ("gender"),
            data .get ("phone"),
            data .get ("email"),
            data .get ("address"),
            bool (data .get ("has_insurance",False )),
            data .get ("insurance_provider"),
            data .get ("policy_number"),
            data .get ("tpa_number"),
            float (data .get ("coverage_limit_inr")or 0 ),
            data .get ("claim_status","Pending Pre-Auth"),
            preferred_tier ,
            requested_bed_id ,
            assigned_ward ,
            data .get ("admitting_department","General Medicine"),
            data .get ("admitting_doctor","Dr. Ramesh Gupta"),
            data .get ("emergency_contact_name"),
            data .get ("emergency_contact_phone"),
            data .get ("emergency_contact_relation"),
            data .get ("clinical_notes")
            ))
            new_admission =cur .fetchone ()


            cur .execute ("""
            UPDATE hospital_beds 
            SET status = 'Occupied', current_patient_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE bed_id = %s;
            """,(patient_id ,requested_bed_id ))

            conn .commit ()
            conn .close ()
            res =dict (new_admission )if new_admission else {}
            if res :
                res ["id"]=res .get ("admission_id")
                res ["patient_name"]=res .get ("full_name")
                res ["preferred_bed_tier"]=res .get ("preferred_bed_type")
                res ["admitted_at"]=res .get ("admission_date")
            return res 
        except Exception as e :
            print (f"[SUPABASE-ERROR] create_admission: {e }")
            raise e 

    @classmethod 
    def list_admissions (cls ,status :Optional [str ]=None ,limit :int =50 )->List [Dict [str ,Any ]]:
        """Lists admissions from Supabase."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )
            query ="SELECT * FROM patient_admissions WHERE 1=1"
            params =[]
            if status :
                query +=" AND status = %s"
                params .append (status )
            query +=" ORDER BY created_at DESC LIMIT %s;"
            params .append (limit )
            cur .execute (query ,params )
            rows =cur .fetchall ()
            conn .close ()
            result =[]
            for r in rows :
                d =dict (r )
                d ["id"]=d .get ("admission_id")
                d ["patient_name"]=d .get ("full_name")
                d ["preferred_bed_tier"]=d .get ("preferred_bed_type")
                d ["admitted_at"]=d .get ("admission_date")
                result .append (d )
            return result 
        except Exception as e :
            print (f"[SUPABASE-ERROR] list_admissions: {e }")
            return []

    @classmethod 
    def discharge_patient (cls ,admission_id :str )->Dict [str ,Any ]:
        """Discharges a patient and atomically marks their assigned bed as Available."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            cur .execute ("""
            UPDATE patient_admissions 
            SET status = 'Discharged', discharge_date = CURRENT_TIMESTAMP
            WHERE admission_id = %s AND status = 'Active'
            RETURNING *;
            """,(admission_id ,))
            admission =cur .fetchone ()

            if admission and admission ["assigned_bed_id"]:
                cur .execute ("""
                UPDATE hospital_beds 
                SET status = 'Available', current_patient_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE bed_id = %s;
                """,(admission ["assigned_bed_id"],))

            conn .commit ()
            conn .close ()
            if admission :
                res =dict (admission )
                res ["id"]=res .get ("admission_id")
                res ["patient_name"]=res .get ("full_name")
                return res 
            return {}
        except Exception as e :
            print (f"[SUPABASE-ERROR] discharge_patient: {e }")
            raise e 




    @classmethod 
    def list_lab_orders (cls ,status :Optional [str ]=None ,limit :int =50 )->List [Dict [str ,Any ]]:
        """Lists laboratory test orders from Supabase."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )
            query ="SELECT * FROM lab_order_to_result WHERE 1=1"
            params =[]
            if status =="Pending":
                query +=" AND resulted_at IS NULL"
            elif status =="Completed":
                query +=" AND resulted_at IS NOT NULL"
            elif status =="Delayed":
                query +=" AND is_delayed = TRUE"

            query +=" ORDER BY ordered_at DESC LIMIT %s;"
            params .append (limit )
            cur .execute (query ,params )
            rows =cur .fetchall ()
            conn .close ()
            return [dict (r )for r in rows ]
        except Exception as e :
            print (f"[SUPABASE-ERROR] list_lab_orders: {e }")
            return []

    @classmethod 
    def update_lab_result (cls ,order_id :str ,is_delayed :Optional [bool ]=None )->Dict [str ,Any ]:
        """Marks a lab test order as Completed in Supabase and recalculates turnaround time."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )


            cur .execute ("SELECT * FROM lab_order_to_result WHERE order_id = %s OR id::text = %s LIMIT 1;",(order_id ,order_id ))
            order =cur .fetchone ()
            if not order :
                conn .close ()
                return {}

            now =datetime .now ()
            ordered_at =order .get ("ordered_at")or now 
            tat_hours =round (max (0.5 ,(now -ordered_at ).total_seconds ()/3600.0 ),1 )
            delayed_flag =is_delayed if is_delayed is not None else (tat_hours >4.0 )

            cur .execute ("""
            UPDATE lab_order_to_result
            SET resulted_at = %s, turnaround_hours = %s, is_delayed = %s
            WHERE order_id = %s OR id::text = %s
            RETURNING *;
            """,(now ,tat_hours ,delayed_flag ,order_id ,order_id ))
            updated =cur .fetchone ()
            conn .commit ()
            conn .close ()
            return dict (updated )if updated else {}
        except Exception as e :
            print (f"[SUPABASE-ERROR] update_lab_result: {e }")
            raise e 




    @classmethod 
    def init_db_schema (cls ):
        """Initializes billing_invoices table and index optimizations in Supabase PostgreSQL."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor ()

            cur .execute ("""
            CREATE TABLE IF NOT EXISTS billing_invoices (
                invoice_id VARCHAR PRIMARY KEY,
                patient_id VARCHAR NOT NULL,
                patient_name VARCHAR NOT NULL,
                bed_id VARCHAR,
                bed_type VARCHAR,
                days_stayed INTEGER,
                daily_bed_rate NUMERIC,
                total_bed_charges NUMERIC,
                total_doctor_charges NUMERIC,
                total_nursing_charges NUMERIC,
                total_lab_charges NUMERIC,
                total_pharmacy_charges NUMERIC,
                gross_subtotal NUMERIC,
                tax_gst NUMERIC,
                gross_total NUMERIC,
                is_insured BOOLEAN,
                insurance_provider VARCHAR,
                policy_number VARCHAR,
                insurance_deduction NUMERIC,
                net_payable NUMERIC,
                status VARCHAR DEFAULT 'Generated',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_invoices_patient ON billing_invoices(patient_id);
            CREATE INDEX IF NOT EXISTS idx_beds_status ON hospital_beds(status);
            CREATE INDEX IF NOT EXISTS idx_admissions_status ON patient_admissions(status);
            """)
            conn .commit ()
            conn .close ()
        except Exception as e :
            print (f"[SUPABASE-ERROR] init_db_schema: {e }")

    @classmethod 
    def update_bed_status (cls ,bed_id :str ,status :str ,current_patient_id :Optional [str ]=None )->Dict [str ,Any ]:
        """Updates bed status directly in Supabase (e.g. Available, Occupied, Needs Cleaning, Maintenance)."""
        try :
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            if status =="Available":
                current_patient_id =None 

            cur .execute ("""
            UPDATE hospital_beds 
            SET status = %s, 
                current_patient_id = COALESCE(%s, current_patient_id),
                updated_at = CURRENT_TIMESTAMP
            WHERE bed_id = %s
            RETURNING *;
            """,(status ,current_patient_id ,bed_id ))
            updated =cur .fetchone ()
            conn .commit ()
            conn .close ()
            return dict (updated )if updated else {}
        except Exception as e :
            print (f"[SUPABASE-ERROR] update_bed_status: {e }")
            raise e 

    @classmethod 
    def save_billing_invoice (cls ,data :Dict [str ,Any ])->Dict [str ,Any ]:
        """Persists an itemized inpatient invoice safely in Supabase."""
        try :
            cls .init_db_schema ()
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )

            invoice_id =data .get ("bill_id")or data .get ("invoice_id")or f"INV-2026-{datetime .now ().strftime ('%m%d%H%M%S')}"

            cur .execute ("""
            INSERT INTO billing_invoices (
                invoice_id, patient_id, patient_name, bed_id, bed_type,
                days_stayed, daily_bed_rate, total_bed_charges, total_doctor_charges,
                total_nursing_charges, total_lab_charges, total_pharmacy_charges,
                gross_subtotal, tax_gst, gross_total, is_insured,
                insurance_provider, policy_number, insurance_deduction, net_payable, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (invoice_id) DO UPDATE SET
                net_payable = EXCLUDED.net_payable,
                status = EXCLUDED.status
            RETURNING *;
            """,(
            invoice_id ,
            data .get ("patient_id"),
            data .get ("patient_name"),
            data .get ("bed_id"),
            data .get ("bed_type"),
            int (data .get ("days_stayed")or 1 ),
            float (data .get ("daily_bed_rate")or 0.0 ),
            float (data .get ("total_bed_charges")or 0.0 ),
            float (data .get ("total_doctor_charges")or 0.0 ),
            float (data .get ("total_nursing_charges")or 0.0 ),
            float (data .get ("total_lab_charges")or 0.0 ),
            float (data .get ("total_pharmacy_charges")or 0.0 ),
            float (data .get ("gross_subtotal")or 0.0 ),
            float (data .get ("tax_gst")or 0.0 ),
            float (data .get ("gross_total")or 0.0 ),
            bool (data .get ("is_insured",False )),
            data .get ("insurance_provider"),
            data .get ("policy_number"),
            float (data .get ("insurance_deduction")or 0.0 ),
            float (data .get ("net_payable")or 0.0 ),
            data .get ("status","Generated")
            ))
            invoice =cur .fetchone ()
            conn .commit ()
            conn .close ()
            return dict (invoice )if invoice else {}
        except Exception as e :
            print (f"[SUPABASE-ERROR] save_billing_invoice: {e }")
            raise e 

    @classmethod 
    def list_billing_invoices (cls ,patient_id :Optional [str ]=None ,limit :int =50 )->List [Dict [str ,Any ]]:
        """Lists persistent billing invoices from Supabase."""
        try :
            cls .init_db_schema ()
            conn =cls .get_connection ()
            cur =conn .cursor (cursor_factory =RealDictCursor )
            sql ="SELECT * FROM billing_invoices WHERE 1=1"
            params =[]
            if patient_id :
                sql +=" AND patient_id = %s"
                params .append (patient_id )
            sql +=" ORDER BY created_at DESC LIMIT %s;"
            params .append (limit )
            cur .execute (sql ,params )
            rows =cur .fetchall ()
            conn .close ()
            return [dict (r )for r in rows ]
        except Exception as e :
            print (f"[SUPABASE-ERROR] list_billing_invoices: {e }")
            return []


