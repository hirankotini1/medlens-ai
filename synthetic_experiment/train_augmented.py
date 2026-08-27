"""
Controlled Synthetic Data Experiment Training & Cross-Validation Engine
Evaluates 4 Tabular Diseases (Anemia, Dengue, Liver, Thyroid) across:
- Baseline (0% Synthetic / Real Only)
- 25% Synthetic Augmentation
- 50% Synthetic Augmentation
- 100% Synthetic Augmentation

Strict Leakage-Free Rules:
1. Exact same Real Test Set for all evaluations.
2. Cross-validation generates synthetic data strictly INSIDE each training fold.
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'disease_prediction', 'datasets'))
SYNTH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'generated_data'))

def get_disease_config(disease):
    if disease == 'anemia':
        return {
            'data_file': os.path.join(DATA_DIR, 'anemia_clean.csv'),
            'target_col': 'Anemia',
            'target_map': {'Anemic': 1, 'Normal': 0},
            'cat_cols': ['Sex'],
            'model': LogisticRegression(random_state=42, max_iter=1000),
            'is_multiclass': False
        }
    elif disease == 'dengue':
        return {
            'data_file': os.path.join(DATA_DIR, 'dengue_clean.csv'),
            'target_col': 'dengue_label',
            'target_map': None,
            'cat_cols': ['gender'],
            'model': RandomForestClassifier(random_state=42, n_estimators=150, max_depth=8),
            'is_multiclass': False
        }
    elif disease == 'liver':
        return {
            'data_file': os.path.join(DATA_DIR, 'liver_clean.csv'),
            'target_col': 'dataset',
            'target_map': {1: 1, 2: 0},
            'cat_cols': ['gender'],
            'model': GradientBoostingClassifier(random_state=42, n_estimators=100),
            'is_multiclass': False
        }
    elif disease == 'thyroid':
        return {
            'data_file': os.path.join(DATA_DIR, 'thyroid_clean.csv'),
            'target_col': 'target',
            'target_map': None,
            'cat_cols': [],
            'model': LogisticRegression(random_state=42, max_iter=1000),
            'is_multiclass': True
        }
    raise ValueError(f"Unknown disease: {disease}")

def build_pipeline(cat_cols, num_cols, model):
    transformers = []
    if cat_cols:
        cat_pipe = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', OneHotEncoder(drop='first', handle_unknown='ignore'))
        ])
        transformers.append(('cat', cat_pipe, cat_cols))
        
    num_pipe = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    transformers.append(('num', num_pipe, num_cols))
    
    preprocessor = ColumnTransformer(transformers=transformers)
    return Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])

def synthesize_fold_data(X_fold, y_fold, cat_cols, num_cols, pct, random_seed):
    if pct == 0:
        return X_fold, y_fold
    
    n_synth = int(np.round(len(X_fold) * (pct / 100.0)))
    classes = np.unique(y_fold)
    synth_X_list = []
    synth_y_list = []
    
    for cls_val in classes:
        mask = (y_fold == cls_val)
        cls_X = X_fold[mask]
        cls_prop = len(cls_X) / len(X_fold)
        n_cls_synth = int(np.round(n_synth * cls_prop))
        if n_cls_synth == 0:
            continue
            
        # Numerical synthesis with covariance
        imputer = SimpleImputer(strategy='median')
        cls_num_arr = imputer.fit_transform(cls_X[num_cols])
        mean_vec = np.mean(cls_num_arr, axis=0)
        cov_mat = np.cov(cls_num_arr, rowvar=False) + np.eye(len(num_cols)) * 1e-3
        
        np.random.seed(random_seed + int(cls_val) * 10 + pct)
        sampled_nums = np.random.multivariate_normal(mean_vec, cov_mat, size=n_cls_synth)
        
        synth_df_cls = pd.DataFrame(sampled_nums, columns=num_cols)
        
        # Categorical synthesis
        for cat_c in cat_cols:
            val_counts = cls_X[cat_c].value_counts(normalize=True)
            cats = list(val_counts.index)
            probs = list(val_counts.values)
            synth_df_cls[cat_c] = np.random.choice(cats, size=n_cls_synth, p=probs)
            
        synth_X_list.append(synth_df_cls)
        synth_y_list.extend([cls_val] * n_cls_synth)
        
    X_synth_combined = pd.concat([X_fold, pd.concat(synth_X_list, ignore_index=True)], ignore_index=True)
    y_synth_combined = pd.concat([pd.Series(y_fold), pd.Series(synth_y_list)], ignore_index=True)
    return X_synth_combined, y_synth_combined

def run_experiment_for_disease(disease):
    cfg = get_disease_config(disease)
    df = pd.read_csv(cfg['data_file'])
    
    if cfg['target_map']:
        y = df[cfg['target_col']].map(cfg['target_map']).astype(int)
    else:
        y = df[cfg['target_col']].astype(int)
        
    X = df.drop(columns=[cfg['target_col']])
    cat_cols = cfg['cat_cols']
    num_cols = [c for c in X.columns if c not in cat_cols]
    
    # 1. Real Train/Test Split (Exact same test set for all models)
    X_train_real, X_test_real, y_train_real, y_test_real = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    results = []
    
    for pct in [0, 25, 50, 100]:
        method_name = "Real Only" if pct == 0 else f"Real + {pct}% Synthetic"
        
        # Load or construct training data for holdout evaluation
        if pct == 0:
            X_train_eval = X_train_real.copy()
            y_train_eval = y_train_real.copy()
        else:
            synth_file = os.path.join(SYNTH_DIR, f"{disease}_synthetic_{pct}.csv")
            synth_df = pd.read_csv(synth_file)
            
            if cfg['target_map']:
                # Synthetic data target might be raw or mapped
                if disease == 'anemia':
                    y_synth = synth_df['Anemia'].map({'Anemic': 1, 'Normal': 0}).astype(int)
                    X_synth = synth_df.drop(columns=['Anemia'])
                elif disease == 'liver':
                    y_synth = synth_df['dataset'].map({1: 1, 2: 0}).astype(int)
                    X_synth = synth_df.drop(columns=['dataset'])
            else:
                y_synth = synth_df[cfg['target_col']].astype(int)
                X_synth = synth_df.drop(columns=[cfg['target_col']])
                
            X_train_eval = pd.concat([X_train_real, X_synth], ignore_index=True)
            y_train_eval = pd.concat([y_train_real, y_synth], ignore_index=True)
            
        # Fit on augmented train set
        pipe = build_pipeline(cat_cols, num_cols, cfg['model'])
        pipe.fit(X_train_eval, y_train_eval)
        
        # Evaluate on UNTOUCHED REAL TEST SET
        y_pred = pipe.predict(X_test_real)
        
        avg_mode = 'macro' if cfg['is_multiclass'] else 'binary'
        holdout_acc = accuracy_score(y_test_real, y_pred)
        holdout_prec = precision_score(y_test_real, y_pred, average=avg_mode, zero_division=0)
        holdout_rec = recall_score(y_test_real, y_pred, average=avg_mode, zero_division=0)
        holdout_f1 = f1_score(y_test_real, y_pred, average=avg_mode, zero_division=0)
        
        # 5-Fold Stratified Cross Validation (Synthetic generation INSIDE training folds)
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_accs, cv_f1s, cv_precs, cv_recs = [], [], [], []
        
        for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X, y)):
            X_tr_f, y_tr_f = X.iloc[tr_idx].reset_index(drop=True), y.iloc[tr_idx].reset_index(drop=True)
            X_val_f, y_val_f = X.iloc[val_idx].reset_index(drop=True), y.iloc[val_idx].reset_index(drop=True)
            
            # Synthesize inside fold
            X_tr_aug, y_tr_aug = synthesize_fold_data(X_tr_f, y_tr_f, cat_cols, num_cols, pct, random_seed=42 + fold_idx)
            
            fold_pipe = build_pipeline(cat_cols, num_cols, cfg['model'])
            fold_pipe.fit(X_tr_aug, y_tr_aug)
            y_val_pred = fold_pipe.predict(X_val_f)
            
            cv_accs.append(accuracy_score(y_val_f, y_val_pred))
            cv_f1s.append(f1_score(y_val_f, y_val_pred, average=avg_mode, zero_division=0))
            cv_precs.append(precision_score(y_val_f, y_val_pred, average=avg_mode, zero_division=0))
            cv_recs.append(recall_score(y_val_f, y_val_pred, average=avg_mode, zero_division=0))
            
        res_dict = {
            'Disease': disease.capitalize(),
            'Training Method': method_name,
            'Synthetic %': f"{pct}%",
            'Train Size': len(X_train_eval),
            'Test Size': len(X_test_real),
            'Holdout Acc': round(holdout_acc, 4),
            'Holdout Prec': round(holdout_prec, 4),
            'Holdout Rec': round(holdout_rec, 4),
            'Holdout F1': round(holdout_f1, 4),
            'CV Acc Mean': round(np.mean(cv_accs), 4),
            'CV Acc Std': round(np.std(cv_accs), 4),
            'CV F1 Mean': round(np.mean(cv_f1s), 4),
            'CV F1 Std': round(np.std(cv_f1s), 4),
            'CV Rec Mean': round(np.mean(cv_recs), 4),
            'CV Prec Mean': round(np.mean(cv_precs), 4),
            'CM': confusion_matrix(y_test_real, y_pred).tolist()
        }
        results.append(res_dict)
        print(f"[{disease.capitalize()}] {method_name} -> Holdout Acc: {holdout_acc:.4f}, Holdout F1: {holdout_f1:.4f} | CV Acc: {np.mean(cv_accs):.4f} ± {np.std(cv_accs):.4f}")
        
    return results

def run_all_experiments():
    print("=" * 70)
    print("      RUNNING CONTROLLED SYNTHETIC DATA EXPERIMENTS (4 DISEASES)")
    print("=" * 70)
    
    all_results = []
    for disease in ['anemia', 'dengue', 'liver', 'thyroid']:
        res = run_experiment_for_disease(disease)
        all_results.extend(res)
        
    return all_results

if __name__ == '__main__':
    from generate_anemia import generate_anemia_synthetic
    from generate_dengue import generate_dengue_synthetic
    from generate_liver import generate_liver_synthetic
    from generate_thyroid import generate_thyroid_synthetic
    
    print("Generating synthetic datasets first...")
    generate_anemia_synthetic()
    generate_dengue_synthetic()
    generate_liver_synthetic()
    generate_thyroid_synthetic()
    
    results = run_all_experiments()
