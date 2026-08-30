"""
Synthetic Data Generator for Dengue Dataset
Strict Leakage-Free Implementation: Only uses Real Training Split (80%)
Generates 25%, 50%, and 100% synthetic augmentations with physiological constraint validation.
"""

import os 
import numpy as np 
import pandas as pd 
from sklearn .model_selection import train_test_split 
from sklearn .impute import SimpleImputer 

DATA_PATH =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','disease_prediction','datasets','dengue_clean.csv'))
OUTPUT_DIR =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'generated_data'))

def generate_dengue_synthetic (random_state =42 ):
    os .makedirs (OUTPUT_DIR ,exist_ok =True )
    df =pd .read_csv (DATA_PATH )

    X =df .drop (columns =['dengue_label'])
    y =df ['dengue_label'].astype (int )


    X_train ,X_test ,y_train ,y_test =train_test_split (
    X ,y ,test_size =0.2 ,random_state =random_state ,stratify =y 
    )

    train_df =X_train .copy ()
    train_df ['dengue_label']=y_train 

    n_train =len (train_df )
    print (f"[Dengue] Real Train set size: {n_train }")


    num_cols =['age','hemoglobin_g_dl','wbc_count','differential_count','rbc_count','platelet_count','platelet_distribution_width']
    imputer =SimpleImputer (strategy ='median')
    train_df_imputed =train_df .copy ()
    train_df_imputed [num_cols ]=imputer .fit_transform (train_df [num_cols ])

    clinical_bounds ={
    'age':(0 ,110 ),
    'hemoglobin_g_dl':(3.0 ,24.0 ),
    'wbc_count':(500 ,30000 ),
    'differential_count':(0 ,1 ),
    'rbc_count':(0 ,1 ),
    'platelet_count':(5000 ,700000 ),
    'platelet_distribution_width':(5.0 ,35.0 )
    }

    percentages =[25 ,50 ,100 ]
    generated_files ={}

    for pct in percentages :
        n_synth =int (np .round (n_train *(pct /100.0 )))
        synth_records =[]

        for cls_label in [0 ,1 ]:
            cls_df =train_df_imputed [train_df_imputed ['dengue_label']==cls_label ]
            cls_prop =len (cls_df )/n_train 
            n_cls_synth =int (np .round (n_synth *cls_prop ))

            mean_vec =cls_df [num_cols ].mean ().values 
            cov_mat =cls_df [num_cols ].cov ().values +np .eye (len (num_cols ))*1e-3 

            np .random .seed (random_state +pct +cls_label *10 )
            sampled_nums =np .random .multivariate_normal (mean_vec ,cov_mat ,size =n_cls_synth *2 )

            gender_prob =cls_df ['gender'].value_counts (normalize =True ).to_dict ()
            categories =list (gender_prob .keys ())
            probs =[gender_prob [c ]for c in categories ]
            sampled_gender =np .random .choice (categories ,size =n_cls_synth *2 ,p =probs )

            valid_rows =[]
            for i in range (len (sampled_nums )):
                row_nums =sampled_nums [i ]
                row_dict ={}
                for val ,col in zip (row_nums ,num_cols ):
                    low ,high =clinical_bounds [col ]
                    clipped_val =np .clip (val ,low ,high )
                    if col in ['age','wbc_count','platelet_count']:
                        row_dict [col ]=int (np .round (clipped_val ))
                    elif col in ['differential_count','rbc_count']:
                        row_dict [col ]=int (np .round (clipped_val ))
                    else :
                        row_dict [col ]=np .round (clipped_val ,2 )

                row_dict ['gender']=sampled_gender [i ]
                row_dict ['dengue_label']=cls_label 
                valid_rows .append (row_dict )
                if len (valid_rows )>=n_cls_synth :
                    break 

            synth_records .extend (valid_rows )

        synth_df =pd .DataFrame (synth_records [:n_synth ])
        synth_df =synth_df .drop_duplicates ()

        filename =f"dengue_synthetic_{pct }.csv"
        file_path =os .path .join (OUTPUT_DIR ,filename )
        synth_df .to_csv (file_path ,index =False )
        generated_files [pct ]=file_path 
        print (f"[Dengue] Generated {len (synth_df )} synthetic samples ({pct }%) -> {filename }")

    return generated_files 

if __name__ =='__main__':
    generate_dengue_synthetic ()
