import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

def train_thyroid_model(data_path=None, model_save_path=None):
    if data_path is None:
        data_path = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'thyroid_clean.csv')
    if model_save_path is None:
        model_save_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'thyroid_pipeline.joblib')
        
    print("=" * 60)
    print("           THYROID MODEL TRAINING PIPELINE (MULTI-CLASS)")
    print("=" * 60)
    
    # 1. Load dataset
    df = pd.read_csv(data_path)
    print(f"Loaded dataset from: {data_path}")
    print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    
    # 2. Features and Target
    # Target: 1 = Normal (Euthyroid), 2 = Hyperthyroidism, 3 = Hypothyroidism
    X = df.drop(columns=['target'])
    y = df['target'].astype(int)
    target_names = ['Normal', 'Hyperthyroid', 'Hypothyroid']
    
    print(f"Target distribution:\n{y.value_counts(normalize=True).round(4) * 100}%")
    print(f"Target count breakdown:\n{y.value_counts()}")
    
    numerical_cols = list(X.columns)
    print(f"Numerical features: {numerical_cols}")
    
    # 3. Train / Test Split (Stratified multi-class split)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # 4. Candidate Models with StandardScaler
    candidate_models = {
        "Multinomial Logistic Regression": LogisticRegression(random_state=42, max_iter=1000),
        "Decision Tree": DecisionTreeClassifier(random_state=42, max_depth=5),
        "Random Forest": RandomForestClassifier(random_state=42, n_estimators=100, max_depth=6),
        "Extra Trees": ExtraTreesClassifier(random_state=42, n_estimators=100, max_depth=6),
        "Support Vector Machine (RBF)": SVC(probability=True, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42, n_estimators=100),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5)
    }
    
    results = []
    trained_pipelines = {}
    
    print("\n--- Model Benchmark Comparison (Weighted & Macro Metrics) ---")
    for name, clf in candidate_models.items():
        pipe = Pipeline(steps=[
            ('scaler', StandardScaler()),
            ('classifier', clf)
        ])
        
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec_weighted = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec_weighted = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1_weighted = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        f1_macro = f1_score(y_test, y_pred, average='macro', zero_division=0)
        
        trained_pipelines[name] = pipe
        results.append({
            'Model': name,
            'Accuracy': acc,
            'F1 (Weighted)': f1_weighted,
            'F1 (Macro)': f1_macro,
            'Precision': prec_weighted,
            'Recall': rec_weighted
        })
        print(f"[{name}] Acc: {acc:.4f} | F1-Weighted: {f1_weighted:.4f} | F1-Macro: {f1_macro:.4f}")
    
    results_df = pd.DataFrame(results).sort_values(by=['F1 (Macro)', 'Accuracy'], ascending=False)
    print("\n" + results_df.to_string(index=False))
    
    # 5. Select best model based on F1-Macro / F1-Weighted
    best_model_name = results_df.iloc[0]['Model']
    best_pipeline = trained_pipelines[best_model_name]
    print(f"\n=> Best Selected Model: {best_model_name}")
    
    y_pred_best = best_pipeline.predict(X_test)
    cm = confusion_matrix(y_test, y_pred_best)
    print("\nConfusion Matrix (Test Set):")
    print(cm)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred_best, target_names=target_names))
    
    # 6. Save complete pipeline with metadata
    save_data = {
        'disease': 'Thyroid',
        'pipeline': best_pipeline,
        'model_name': best_model_name,
        'feature_names': list(X.columns),
        'numerical_features': numerical_cols,
        'target_mapping': {1: 'Normal', 2: 'Hyperthyroid', 3: 'Hypothyroid'},
        'metrics': results_df.iloc[0].to_dict()
    }
    
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(save_data, model_save_path)
    print(f"Successfully saved full pipeline to: {model_save_path}")
    return save_data

if __name__ == '__main__':
    train_thyroid_model()
