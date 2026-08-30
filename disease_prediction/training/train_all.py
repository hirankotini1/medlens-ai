import os 
import sys 
import time 
import pandas as pd 


sys .path .insert (0 ,os .path .dirname (__file__ ))

from train_anemia import train_anemia_model 
from train_dengue import train_dengue_model 
from train_liver import train_liver_model 
from train_thyroid import train_thyroid_model 
from train_malaria import train_malaria_model 

def run_all_trainers ():
    start_time =time .time ()
    print ("="*70 )
    print ("       STARTING COMPLETE MULTI-DISEASE MODEL TRAINING PIPELINE")
    print ("="*70 )

    summary =[]


    print ("\n>>> [1/5] Training Anemia Models...")
    res_anemia =train_anemia_model ()
    summary .append ({
    'Disease':'Anemia',
    'Type':'Tabular (7 Features)',
    'Selected Algorithm':res_anemia ['model_name'],
    'Accuracy':f"{res_anemia ['metrics']['Accuracy']:.4f}",
    'Precision':f"{res_anemia ['metrics']['Precision']:.4f}",
    'Recall':f"{res_anemia ['metrics']['Recall']:.4f}",
    'F1-Score':f"{res_anemia ['metrics']['F1-Score']:.4f}",
    'Model File':'anemia_pipeline.joblib'
    })


    print ("\n>>> [2/5] Training Dengue Models...")
    res_dengue =train_dengue_model ()
    summary .append ({
    'Disease':'Dengue',
    'Type':'Tabular (8 Features)',
    'Selected Algorithm':res_dengue ['model_name'],
    'Accuracy':f"{res_dengue ['metrics']['Accuracy']:.4f}",
    'Precision':f"{res_dengue ['metrics']['Precision']:.4f}",
    'Recall':f"{res_dengue ['metrics']['Recall']:.4f}",
    'F1-Score':f"{res_dengue ['metrics']['F1-Score']:.4f}",
    'Model File':'dengue_pipeline.joblib'
    })


    print ("\n>>> [3/5] Training Liver Disease Models...")
    res_liver =train_liver_model ()
    summary .append ({
    'Disease':'Liver Disease',
    'Type':'Tabular (10 Features)',
    'Selected Algorithm':res_liver ['model_name'],
    'Accuracy':f"{res_liver ['metrics']['Accuracy']:.4f}",
    'Precision':f"{res_liver ['metrics']['Precision']:.4f}",
    'Recall':f"{res_liver ['metrics']['Recall']:.4f}",
    'F1-Score':f"{res_liver ['metrics']['F1-Score']:.4f}",
    'Model File':'liver_pipeline.joblib'
    })


    print ("\n>>> [4/5] Training Thyroid Models...")
    res_thyroid =train_thyroid_model ()
    summary .append ({
    'Disease':'Thyroid',
    'Type':'Tabular Multi-class (5 Features)',
    'Selected Algorithm':res_thyroid ['model_name'],
    'Accuracy':f"{res_thyroid ['metrics']['Accuracy']:.4f}",
    'Precision':f"{res_thyroid ['metrics']['Precision']:.4f}",
    'Recall':f"{res_thyroid ['metrics']['Recall']:.4f}",
    'F1-Score':f"{res_thyroid ['metrics']['F1 (Weighted)']:.4f}",
    'Model File':'thyroid_pipeline.joblib'
    })


    print ("\n>>> [5/5] Training Malaria Image Classification Models...")
    res_malaria =train_malaria_model ()
    summary .append ({
    'Disease':'Malaria',
    'Type':'Computer Vision (Microscopy Images)',
    'Selected Algorithm':res_malaria ['model_name'],
    'Accuracy':f"{res_malaria ['metrics']['Accuracy']:.4f}",
    'Precision':f"{res_malaria ['metrics']['Precision']:.4f}",
    'Recall':f"{res_malaria ['metrics']['Recall']:.4f}",
    'F1-Score':f"{res_malaria ['metrics']['F1-Score']:.4f}",
    'Model File':'malaria_pipeline.joblib'
    })

    total_time =time .time ()-start_time 
    print ("\n"+"="*80 )
    print ("                     FINAL TRAINING BENCHMARK SUMMARY")
    print ("="*80 )
    summary_df =pd .DataFrame (summary )
    print (summary_df .to_string (index =False ))
    print (f"\nAll 5 models trained, validated, and saved in {total_time :.2f} seconds.")
    print ("Artifacts saved to: disease_prediction/models/")
    print ("="*80 )

if __name__ =='__main__':
    run_all_trainers ()
