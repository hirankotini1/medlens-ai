import os 
import shutil 

BASE_DIR =os .path .join (os .getcwd (),'disease_prediction')
DATASETS_DIR =os .path .join (BASE_DIR ,'datasets')
MODELS_DIR =os .path .join (BASE_DIR ,'models')
TRAINING_DIR =os .path .join (BASE_DIR ,'training')
API_DIR =os .path .join (BASE_DIR ,'api')

for d in [BASE_DIR ,DATASETS_DIR ,MODELS_DIR ,TRAINING_DIR ,API_DIR ]:
    os .makedirs (d ,exist_ok =True )
    print (f"Ensured directory exists: {d }")


csv_files =['anemia_clean.csv','dengue_clean.csv','liver_clean.csv','thyroid_clean.csv']
for f in csv_files :
    if os .path .exists (f ):
        dst =os .path .join (DATASETS_DIR ,f )
        shutil .copy2 (f ,dst )
        print (f"Copied {f } -> {dst }")


malaria_src ='malaria_simple'
malaria_dst =os .path .join (DATASETS_DIR ,'malaria_simple')
if os .path .exists (malaria_src ):
    if os .path .exists (malaria_dst ):
        shutil .rmtree (malaria_dst )
    shutil .copytree (malaria_src ,malaria_dst )
    print (f"Copied {malaria_src } -> {malaria_dst }")

print ("Directory structure successfully initialized.")
