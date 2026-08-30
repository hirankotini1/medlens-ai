import os 
import sys 
from fastapi .testclient import TestClient 


sys .path .insert (0 ,os .path .join (os .path .dirname (__file__ ),'api'))
sys .path .insert (0 ,os .path .join (os .path .dirname (__file__ ),'training'))

from main import app 

client =TestClient (app )

def test_root ():
    response =client .get ("/")
    assert response .status_code ==200 ,f"Failed: {response .text }"
    assert "text/html"in response .headers .get ("content-type","")or "html"in response .text .lower ()
    print ("  [PASSED] GET / (Interactive Web UI Frontend served)")

def test_health ():
    response =client .get ("/health")
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["status"]=="ok"
    print ("  [PASSED] GET /health (Lightweight keep-alive verified HTTP 200 OK)")

def test_predict_anemia_positive ():
    payload ={
    "Age":28 ,
    "Sex":"Female",
    "HGB":8.5 ,
    "RBC":3.8 ,
    "PCV":27.0 ,
    "MCV":71.0 ,
    "MCH":22.0 ,
    "MCHC":29.0 ,
    "RDW":18.5 ,
    "TLC":6.8 ,
    "PLT /mm3":195.0 
    }
    response =client .post ("/predict/anemia",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Anemia"
    assert "prediction"in data 
    assert 0.0 <=data ["confidence"]<=1.0 
    assert "disclaimer"in data 
    print (f"  [PASSED] POST /predict/anemia -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_predict_anemia_negative ():
    payload ={
    "Age":35 ,
    "Sex":"Male",
    "HGB":15.5 ,
    "RBC":5.2 ,
    "PCV":46.0 ,
    "MCV":88.0 ,
    "MCH":29.8 ,
    "MCHC":33.7 ,
    "RDW":13.0 ,
    "TLC":7.2 ,
    "PLT /mm3":250.0 
    }
    response =client .post ("/predict/anemia",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Anemia"
    assert data ["prediction"]=="Normal"
    print (f"  [PASSED] POST /predict/anemia (Normal sample) -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_predict_dengue ():
    payload ={
    "age":43 ,
    "gender":"Male",
    "hemoglobin_g_dl":12.6 ,
    "wbc_count":2200.0 ,
    "differential_count":1 ,
    "rbc_count":1 ,
    "platelet_count":62000.0 ,
    "platelet_distribution_width":11.0 
    }
    response =client .post ("/predict/dengue",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Dengue"
    assert "prediction"in data 
    assert 0.0 <=data ["confidence"]<=1.0 
    print (f"  [PASSED] POST /predict/dengue -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_predict_dengue_missing_optional_fields ():
    payload ={
    "age":25 ,
    "gender":"Female",
    "hemoglobin_g_dl":13.5 ,
    "differential_count":0 ,
    "rbc_count":0 
    }
    response =client .post ("/predict/dengue",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Dengue"
    print (f"  [PASSED] POST /predict/dengue (Missing optional lab fields imputed) -> Pred: {data ['prediction']}")

def test_predict_liver ():
    payload ={
    "age":65 ,
    "gender":"Female",
    "total_bilirubin":0.7 ,
    "direct_bilirubin":0.1 ,
    "alkaline_phosphotase":187 ,
    "alamine_aminotransferase":16 ,
    "aspartate_aminotransferase":18 ,
    "total_protiens":6.8 ,
    "albumin":3.3 ,
    "albumin_and_globulin_ratio":0.9 
    }
    response =client .post ("/predict/liver",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Liver Disease"
    assert "prediction"in data 
    assert 0.0 <=data ["confidence"]<=1.0 
    print (f"  [PASSED] POST /predict/liver -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_predict_thyroid ():
    payload ={
    "TSH":0.9 ,
    "T4":10.1 ,
    "T3":2.2 ,
    "TSH_response":2.7 ,
    "T3_resin_uptake":107 
    }
    response =client .post ("/predict/thyroid",json =payload )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Thyroid Disorder"
    assert "prediction"in data 
    assert 0.0 <=data ["confidence"]<=1.0 
    print (f"  [PASSED] POST /predict/thyroid -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_predict_malaria_image ():
    sample_img_path =os .path .join (
    os .path .dirname (__file__ ),
    'datasets','malaria_simple','test','parasite',
    os .listdir (os .path .join (os .path .dirname (__file__ ),'datasets','malaria_simple','test','parasite'))[0 ]
    )
    with open (sample_img_path ,'rb')as f :
        response =client .post (
        "/predict/malaria",
        files ={"file":("test_cell.png",f ,"image/png")}
        )
    assert response .status_code ==200 ,f"Failed: {response .text }"
    data =response .json ()
    assert data ["disease"]=="Malaria"
    assert data ["prediction"]in ["Parasite Detected","Uninfected / Clear"]
    assert 0.0 <=data ["confidence"]<=1.0 
    print (f"  [PASSED] POST /predict/malaria (Image file upload) -> Pred: {data ['prediction']}, Conf: {data ['confidence']}")

def test_validation_error_handling ():
    payload ={
    "Age":-5 ,
    "Sex":"Female",
    "HGB":10.0 ,
    "RBC":4.0 ,
    "PCV":35.0 ,
    "MCV":80.0 ,
    "MCH":25.0 ,
    "MCHC":30.0 ,
    "RDW":15.0 ,
    "TLC":7.0 ,
    "PLT /mm3":200.0 
    }
    response =client .post ("/predict/anemia",json =payload )
    assert response .status_code ==422 
    print ("  [PASSED] Input Validation: Invalid negative values rejected with HTTP 422 Unprocessable Entity")

if __name__ =='__main__':
    print ("="*60 )
    print ("         RUNNING FASTAPI PREDICTION TEST SUITE")
    print ("="*60 )
    test_root ()
    test_health ()
    test_predict_anemia_positive ()
    test_predict_anemia_negative ()
    test_predict_dengue ()
    test_predict_dengue_missing_optional_fields ()
    test_predict_liver ()
    test_predict_thyroid ()
    test_predict_malaria_image ()
    test_validation_error_handling ()
    print ("="*60 )
    print (">>> ALL API TESTS PASSED SUCCESSFULLY! (10/10 tests passed)")
    print ("="*60 )
