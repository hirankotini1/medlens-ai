import os
import pandas as pd
import numpy as np

print("=== DATASET INSPECTION SCRIPT ===")
datasets = {
    'anemia': 'anemia_clean.csv',
    'dengue': 'dengue_clean.csv',
    'liver': 'liver_clean.csv',
    'thyroid': 'thyroid_clean.csv'
}

for name, path in datasets.items():
    print(f"\n================= {name.upper()} ({path}) =================")
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        print(f"Columns: {list(df.columns)}")
        print(f"Data types:\n{df.dtypes}")
        print(f"Missing values:\n{df.isnull().sum()}")
        print(f"Duplicate rows: {df.duplicated().sum()}")
        print(f"Summary Statistics:\n{df.describe(include='all')}")
        print("Target / Unique Values Check:")
        for col in df.columns:
            val_counts = df[col].value_counts()
            if len(val_counts) <= 10:
                print(f"  {col} distribution:\n{val_counts}")
            else:
                print(f"  {col}: {len(val_counts)} unique values (range: {df[col].min()} to {df[col].max()})")
    else:
        print(f"File {path} not found!")

print("\n================= MALARIA DATASET =================")
malaria_path = 'malaria_simple'
if os.path.exists(malaria_path):
    total_imgs = 0
    for root, dirs, files in os.walk(malaria_path):
        imgs = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if imgs:
            print(f"Directory: {root} -> {len(imgs)} images. Example files: {imgs[:3]}")
            total_imgs += len(imgs)
    print(f"Total malaria images found: {total_imgs}")
else:
    print("Malaria path not found.")
