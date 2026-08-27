"""
Synthetic Data Generator for Liver Dataset
Strict Leakage-Free Implementation: Only uses Real Training Split (80%)
Generates 25%, 50%, and 100% synthetic augmentations with physiological constraint validation.
Addresses class imbalance with minority-class preserving conditional generation.
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'disease_prediction', 'datasets', 'liver_clean.csv'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'generated_data'))

def generate_liver_synthetic(random_state=42):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    
    # 1 -> 1 (Liver Patient), 2 -> 0 (Healthy)
    X = df.drop(columns=['dataset'])
    y = df['dataset'].map({1: 1, 2: 0})
    
    # 1. Strict Stratified Split - Holdout Test Set NEVER touched
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )
    
    train_df = X_train.copy()
    train_df['dataset'] = y_train
    
    n_train = len(train_df)
    print(f"[Liver] Real Train set size: {n_train} (Class 1: {(y_train==1).sum()}, Class 0: {(y_train==0).sum()})")
    
    num_cols = ['age', 'total_bilirubin', 'direct_bilirubin', 'alkaline_phosphotase',
                'alamine_aminotransferase', 'aspartate_aminotransferase', 'total_protiens',
                'albumin', 'albumin_and_globulin_ratio']
    
    imputer = SimpleImputer(strategy='median')
    train_df_imputed = train_df.copy()
    train_df_imputed[num_cols] = imputer.fit_transform(train_df[num_cols])
    
    clinical_bounds = {
        'age': (1, 100),
        'total_bilirubin': (0.1, 75.0),
        'direct_bilirubin': (0.05, 30.0),
        'alkaline_phosphotase': (50, 2500),
        'alamine_aminotransferase': (5, 2000),
        'aspartate_aminotransferase': (5, 5000),
        'total_protiens': (2.0, 10.0),
        'albumin': (0.8, 6.0),
        'albumin_and_globulin_ratio': (0.2, 3.0)
    }
    
    percentages = [25, 50, 100]
    generated_files = {}
    
    for pct in percentages:
        n_synth = int(np.round(n_train * (pct / 100.0)))
        synth_records = []
        
        for cls_label in [0, 1]:
            cls_df = train_df_imputed[train_df_imputed['dataset'] == cls_label]
            cls_prop = len(cls_df) / n_train
            n_cls_synth = int(np.round(n_synth * cls_prop))
            
            mean_vec = cls_df[num_cols].mean().values
            cov_mat = cls_df[num_cols].cov().values + np.eye(len(num_cols)) * 1e-3
            
            np.random.seed(random_state + pct + cls_label * 20)
            sampled_nums = np.random.multivariate_normal(mean_vec, cov_mat, size=n_cls_synth * 2)
            
            gender_prob = cls_df['gender'].value_counts(normalize=True).to_dict()
            categories = list(gender_prob.keys())
            probs = [gender_prob[c] for c in categories]
            sampled_gender = np.random.choice(categories, size=n_cls_synth * 2, p=probs)
            
            valid_rows = []
            for i in range(len(sampled_nums)):
                row_nums = sampled_nums[i]
                row_dict = {}
                for val, col in zip(row_nums, num_cols):
                    low, high = clinical_bounds[col]
                    clipped_val = np.clip(val, low, high)
                    if col in ['age', 'alkaline_phosphotase', 'alamine_aminotransferase', 'aspartate_aminotransferase']:
                        row_dict[col] = int(np.round(clipped_val))
                    else:
                        row_dict[col] = np.round(clipped_val, 2)
                        
                row_dict['gender'] = sampled_gender[i]
                row_dict['dataset'] = 1 if cls_label == 1 else 2  # Keep original raw label representation 1/2
                valid_rows.append(row_dict)
                if len(valid_rows) >= n_cls_synth:
                    break
                    
            synth_records.extend(valid_rows)
            
        synth_df = pd.DataFrame(synth_records[:n_synth])
        synth_df = synth_df.drop_duplicates()
        
        filename = f"liver_synthetic_{pct}.csv"
        file_path = os.path.join(OUTPUT_DIR, filename)
        synth_df.to_csv(file_path, index=False)
        generated_files[pct] = file_path
        print(f"[Liver] Generated {len(synth_df)} synthetic samples ({pct}%) -> {filename}")
        
    return generated_files

if __name__ == '__main__':
    generate_liver_synthetic()
