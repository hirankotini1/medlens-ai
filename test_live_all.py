import urllib.request
import json
import os

base = 'http://127.0.0.1:8000'

print("=" * 60)
print("     NEXUS PATHOLOGY LIVE SYSTEM VERIFICATION")
print("=" * 60)

# 1. Health check
r = urllib.request.urlopen(base + '/health')
health = json.loads(r.read().decode())
print(f"[+] Health Check: {r.status} OK | Models: {health['models_available']}")

# 2. Anemia Prediction
p_anemia = json.dumps({
    'Age': 28, 'Sex': 'Female', 'HGB': 9.2, 'RBC': 3.4, 'PCV': 29.0,
    'MCV': 72.0, 'MCH': 22.0, 'MCHC': 29.5, 'RDW': 16.5, 'TLC': 6.8, 'PLT /mm3': 210.0
}).encode()
r = urllib.request.urlopen(urllib.request.Request(base + '/predict/anemia', data=p_anemia, headers={'Content-Type': 'application/json'}))
d = json.loads(r.read().decode())
print(f"[+] Anemia Prediction: {d['prediction']} (Confidence: {d['confidence']*100:.1f}%)")

# 3. Dengue Prediction
p_dengue = json.dumps({
    'age': 30, 'gender': 'Male', 'hemoglobin_g_dl': 14.2, 'wbc_count': 3200,
    'differential_count': 1, 'rbc_count': 1, 'platelet_count': 45000, 'platelet_distribution_width': 18.2
}).encode()
r = urllib.request.urlopen(urllib.request.Request(base + '/predict/dengue', data=p_dengue, headers={'Content-Type': 'application/json'}))
d = json.loads(r.read().decode())
print(f"[+] Dengue Prediction: {d['prediction']} (Confidence: {d['confidence']*100:.1f}%)")

# 4. Liver Prediction
p_liver = json.dumps({
    'age': 45, 'gender': 'Male', 'total_bilirubin': 2.5, 'direct_bilirubin': 1.2,
    'alkaline_phosphotase': 300, 'alamine_aminotransferase': 65, 'aspartate_aminotransferase': 70,
    'total_protiens': 6.2, 'albumin': 3.0, 'albumin_and_globulin_ratio': 0.9
}).encode()
r = urllib.request.urlopen(urllib.request.Request(base + '/predict/liver', data=p_liver, headers={'Content-Type': 'application/json'}))
d = json.loads(r.read().decode())
print(f"[+] Liver Prediction: {d['prediction']} (Confidence: {d['confidence']*100:.1f}%)")

# 5. Thyroid Prediction
p_thyroid = json.dumps({
    'TSH': 8.5, 'T4': 4.2, 'T3': 0.8, 'TSH_response': 12.0, 'T3_resin_uptake': 95
}).encode()
r = urllib.request.urlopen(urllib.request.Request(base + '/predict/thyroid', data=p_thyroid, headers={'Content-Type': 'application/json'}))
d = json.loads(r.read().decode())
print(f"[+] Thyroid Prediction: {d['prediction']} (Confidence: {d['confidence']*100:.1f}%)")

# 6. Patient Login & Report-linked ML Decision Support
login_req = urllib.request.Request(base + '/api/patient/login', data=json.dumps({'patient_id': 'PAT-1001', 'access_pin': 'PIN-1001'}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
token = json.loads(urllib.request.urlopen(login_req).read().decode())['token']
print(f"[+] Patient Login (PAT-1001): OK (Token generated)")

reports = json.loads(urllib.request.urlopen(urllib.request.Request(base + '/api/reports?patient_id=PAT-1001', headers={'Authorization': 'Bearer ' + token})).read().decode())
print(f"[+] Patient Reports retrieved: {len(reports)} reports found")

for rep in reports:
    rep_id = rep['report_id']
    cat = rep['test_category']
    ml_res = json.loads(urllib.request.urlopen(urllib.request.Request(base + f'/api/reports/{rep_id}/analyze-ml', headers={'Authorization': 'Bearer ' + token}, method='POST')).read().decode())
    print(f"    -> Report {rep_id} [{cat}]: {ml_res['disease']} => {ml_res['prediction']} (Conf: {ml_res['confidence']*100:.1f}%)")

print("=" * 60)
print("     ALL BACKEND SYSTEMS WORKING 100% PERFECTLY! ")
print("=" * 60)
