import urllib .request 
import json 
import uuid 
import sys 
import os 

sys .path .insert (0 ,os .path .abspath (os .path .join (os .path .dirname (__file__ ),"..")))
from disease_prediction .test_pdf_extraction import generate_full_synthetic_pdf 

def test_live_endpoint ():
    pdf_bytes =generate_full_synthetic_pdf ()
    boundary ="----WebKitFormBoundary"+uuid .uuid4 ().hex [:16 ]

    body =(
    f"--{boundary }\r\n"
    f'Content-Disposition: form-data; name="file"; filename="patient_health_report.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
    ).encode ("utf-8")+pdf_bytes +f"\r\n--{boundary }--\r\n".encode ("utf-8")

    req =urllib .request .Request (
    "http://127.0.0.1:8000/api/analyzer/extract",
    data =body ,
    headers ={"Content-Type":f"multipart/form-data; boundary={boundary }"},
    method ="POST"
    )

    with urllib .request .urlopen (req ,timeout =30 )as resp :
        res =json .loads (resp .read ().decode ("utf-8"))
        print ("="*70 )
        print ("  LIVE HTTP PDF EXTRACTION ENDPOINT TEST")
        print ("="*70 )
        print ("HTTP Status:",resp .status )
        print ("Filename:",res ["filename"])
        print ("Parameters Extracted Count:",res ["total_parameters"])
        print ("Data Quality:",res ["data_quality"])

        param_map ={p ["parameter"]:p for p in res ["parameters"]}
        assert len (res ["parameters"])>=24 ,f"Expected >= 24 parameters, got {len (res ['parameters'])}"


        assert param_map ["24-Hour Urinary Copper"]["value"]==35.0 
        assert "ug/24h"in param_map ["24-Hour Urinary Copper"]["unit"]

        assert param_map ["T3"]["value"]==1.2 
        assert "ng/mL"in param_map ["T3"]["unit"]

        assert param_map ["T4"]["value"]==8.0 
        assert "ug/dL"in param_map ["T4"]["unit"]

        assert param_map ["T3 Resin Uptake"]["value"]==32.0 
        assert "%"in param_map ["T3 Resin Uptake"]["unit"]

        print ("\nAll critical values verified over live HTTP!")
        print ("="*70 )

if __name__ =="__main__":
    test_live_endpoint ()
