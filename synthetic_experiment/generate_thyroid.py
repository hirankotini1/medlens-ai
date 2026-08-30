"""
Synthetic Data Generator for Thyroid Dataset (Multi-Class: 1, 2, 3)
Strict Leakage-Free Implementation: Only uses Real Training Split (80%)
Generates 25%, 50%, and 100% synthetic augmentations with physiological constraint validation.
"""

import os 
import numpy as np 
import pandas as pd 
from sklearn .model_selection import train_test_split 

DATA_PATH =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','disease_prediction','datasets','thyroid_clean.csv'))
OUTPUT_DIR =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'generated_data'))

def generate_thyroid_synthetic (random_state =42 ):
    os .makedirs (OUTPUT_DIR ,exist_ok =True )
    df =pd .read_csv (DATA_PATH )


    X =df .drop (columns =['target'])
    y =df ['target'].astype (int )


    X_train ,X_test ,y_train ,y_test =train_test_split (
    X ,y ,test_size =0.2 ,random_state =random_state ,stratify =y 
    )

    train_df =X_train .copy ()
    train_df ['target']=y_train 

    n_train =len (train_df )
    print (f"[Thyroid] Real Train set size: {n_train } (Class 1: {(y_train ==1 ).sum ()}, Class 2: {(y_train ==2 ).sum ()}, Class 3: {(y_train ==3 ).sum ()})")

    num_cols =list (X .columns )

    clinical_bounds ={
    'TSH':(0.01 ,100.0 ),
    'T4':(0.1 ,40.0 ),
    'T3':(0.05 ,20.0 ),
    'TSH_response':(-5.0 ,100.0 ),
    'T3_resin_uptake':(40 ,200 )
    }

    percentages =[25 ,50 ,100 ]
    generated_files ={}

    for pct in percentages :
        n_synth =int (np .round (n_train *(pct /100.0 )))
        synth_records =[]

        for cls_label in [1 ,2 ,3 ]:
            cls_df =train_df [train_df ['target']==cls_label ]
            cls_prop =len (cls_df )/n_train 
            n_cls_synth =int (np .round (n_synth *cls_prop ))

            mean_vec =cls_df [num_cols ].mean ().values 
            cov_mat =cls_df [num_cols ].cov ().values +np .eye (len (num_cols ))*1e-3 

            np .random .seed (random_state +pct +cls_label *30 )
            sampled_nums =np .random .multivariate_normal (mean_vec ,cov_mat ,size =n_cls_synth *2 )

            valid_rows =[]
            for i in range (len (sampled_nums )):
                row_nums =sampled_nums [i ]
                row_dict ={}
                for val ,col in zip (row_nums ,num_cols ):
                    low ,high =clinical_bounds [col ]
                    clipped_val =np .clip (val ,low ,high )
                    if col =='T3_resin_uptake':
                        row_dict [col ]=int (np .round (clipped_val ))
                    else :
                        row_dict [col ]=np .round (clipped_val ,2 )

                row_dict ['target']=cls_label 
                valid_rows .append (row_dict )
                if len (valid_rows )>=n_cls_synth :
                    break 

            synth_records .extend (valid_rows )

        synth_df =pd .DataFrame (synth_records [:n_synth ])
        synth_df =synth_df .drop_duplicates ()

        filename =f"thyroid_synthetic_{pct }.csv"
        file_path =os .path .join (OUTPUT_DIR ,filename )
        synth_df .to_csv (file_path ,index =False )
        generated_files [pct ]=file_path 
        print (f"[Thyroid] Generated {len (synth_df )} synthetic samples ({pct }%) -> {filename }")

    return generated_files 

if __name__ =='__main__':
    generate_thyroid_synthetic ()
