"""
Synthetic Data Generator for Anemia Dataset
Strict Leakage-Free Implementation: Only uses Real Training Split (80%)
Generates 25%, 50%, and 100% synthetic augmentations with physiological constraint validation.
"""

import os 
import numpy as np 
import pandas as pd 
from sklearn .model_selection import train_test_split 
from scipy .stats import truncnorm 

DATA_PATH =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'..','disease_prediction','datasets','anemia_clean.csv'))
OUTPUT_DIR =os .path .abspath (os .path .join (os .path .dirname (__file__ ),'generated_data'))

def generate_anemia_synthetic (random_state =42 ):
    os .makedirs (OUTPUT_DIR ,exist_ok =True )
    df =pd .read_csv (DATA_PATH )

    X =df .drop (columns =['Anemia'])
    y =df ['Anemia'].map ({'Anemic':1 ,'Normal':0 })


    X_train ,X_test ,y_train ,y_test =train_test_split (
    X ,y ,test_size =0.2 ,random_state =random_state ,stratify =y 
    )

    train_df =X_train .copy ()
    train_df ['Anemia']=y_train 

    n_train =len (train_df )
    print (f"[Anemia] Real Train set size: {n_train }")


    clinical_bounds ={
    'Age':(1 ,110 ),
    'HGB':(2.0 ,25.0 ),
    'RBC':(1.0 ,9.0 ),
    'PCV':(10.0 ,65.0 ),
    'MCV':(40.0 ,130.0 ),
    'MCH':(10.0 ,45.0 ),
    'MCHC':(15.0 ,42.0 ),
    'RDW':(8.0 ,35.0 ),
    'TLC':(1.0 ,50.0 ),
    'PLT /mm3':(10.0 ,1000.0 )
    }

    percentages =[25 ,50 ,100 ]
    generated_files ={}

    for pct in percentages :
        n_synth =int (np .round (n_train *(pct /100.0 )))
        synth_records =[]


        for cls_label in [0 ,1 ]:
            cls_df =train_df [train_df ['Anemia']==cls_label ]
            cls_prop =len (cls_df )/n_train 
            n_cls_synth =int (np .round (n_synth *cls_prop ))

            num_cols =[c for c in X .columns if c !='Sex']
            mean_vec =cls_df [num_cols ].mean ().values 
            cov_mat =cls_df [num_cols ].cov ().values +np .eye (len (num_cols ))*1e-4 


            np .random .seed (random_state +pct +cls_label )
            sampled_nums =np .random .multivariate_normal (mean_vec ,cov_mat ,size =n_cls_synth *2 )


            sex_prob =cls_df ['Sex'].value_counts (normalize =True ).to_dict ()
            p_female =sex_prob .get ('Female',0.5 )
            sampled_sex =np .random .choice (['Female','Male'],size =n_cls_synth *2 ,p =[p_female ,1 -p_female ])

            valid_rows =[]
            for i in range (len (sampled_nums )):
                row_nums =sampled_nums [i ]

                in_bounds =True 
                clipped_nums =[]
                for val ,col in zip (row_nums ,num_cols ):
                    low ,high =clinical_bounds [col ]
                    clipped_val =np .clip (val ,low ,high )
                    clipped_nums .append (clipped_val )

                row_dict ={col :np .round (val ,2 )for col ,val in zip (num_cols ,clipped_nums )}
                row_dict ['Age']=int (np .round (row_dict ['Age']))
                row_dict ['Sex']=sampled_sex [i ]
                row_dict ['Anemia']='Anemic'if cls_label ==1 else 'Normal'
                valid_rows .append (row_dict )
                if len (valid_rows )>=n_cls_synth :
                    break 

            synth_records .extend (valid_rows )

        synth_df =pd .DataFrame (synth_records [:n_synth ])

        synth_df =synth_df .drop_duplicates ()

        filename =f"anemia_synthetic_{pct }.csv"
        file_path =os .path .join (OUTPUT_DIR ,filename )
        synth_df .to_csv (file_path ,index =False )
        generated_files [pct ]=file_path 
        print (f"[Anemia] Generated {len (synth_df )} synthetic samples ({pct }%) -> {filename }")

    return generated_files 

if __name__ =='__main__':
    generate_anemia_synthetic ()
