import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

def train_dengue_model(data_path=None, model_save_path=None):
    if data_path is None:
        data_path = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'dengue_clean.csv')
    if model_save_path is None:
        model_save_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'dengue_pipeline.joblib')
        
    print("=" * 60)
    print("           DENGUE MODEL TRAINING PIPELINE")
    print("=" * 60)
    
    # 1. Load dataset
    df = pd.read_csv(data_path)
    print(f"Loaded dataset from: {data_path}")
    print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    
    # 2. Features and Target
    X = df.drop(columns=['dengue_label'])
    y = df['dengue_label'].astype(int)
    target_names = ['Negative', 'Positive']
    
    print(f"Target distribution:\n{y.value_counts(normalize=True).round(4) * 100}%")
    print(f"Missing values before split:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    
    categorical_cols = ['gender']
    numerical_cols = [c for c in X.columns if c not in categorical_cols]
    print(f"Categorical features: {categorical_cols}")
    print(f"Numerical features: {numerical_cols}")
    
    # 3. Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # 4. Preprocessing Pipeline with Imputation to prevent leakage
    num_pipeline = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    cat_pipeline = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('encoder', OneHotEncoder(drop='first', handle_unknown='ignore'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', cat_pipeline, categorical_cols),
            ('num', num_pipeline, numerical_cols)
        ]
    )
    
    # 5. Candidate Models
    candidate_models = {
        "Logistic Regression": LogisticRegression(random_state=42, max_iter=1000),
        "Decision Tree": DecisionTreeClassifier(random_state=42, max_depth=6),
        "Random Forest": RandomForestClassifier(random_state=42, n_estimators=150, max_depth=8),
        "Extra Trees": ExtraTreesClassifier(random_state=42, n_estimators=150, max_depth=8),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42, n_estimators=100),
        "Support Vector Machine (RBF)": SVC(probability=True, random_state=42),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5)
    }
    
    results = []
    trained_pipelines = {}
    
    print("\n--- Model Benchmark Comparison ---")
    for name, clf in candidate_models.items():
        pipe = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', clf)
        ])
        
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        trained_pipelines[name] = pipe
        results.append({
            'Model': name,
            'Accuracy': acc,
            'Precision': prec,
            'Recall': rec,
            'F1-Score': f1
        })
        print(f"[{name}] Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}")
    
    results_df = pd.DataFrame(results).sort_values(by=['F1-Score', 'Accuracy'], ascending=False)
    print("\n" + results_df.to_string(index=False))
    
    # 6. Select best model based on F1-Score (balanced metric)
    best_model_name = results_df.iloc[0]['Model']
    best_pipeline = trained_pipelines[best_model_name]
    print(f"\n=> Best Selected Model: {best_model_name}")
    
    y_pred_best = best_pipeline.predict(X_test)
    cm = confusion_matrix(y_test, y_pred_best)
    print("\nConfusion Matrix (Test Set):")
    print(cm)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred_best, target_names=target_names))
    
    # 7. Save complete pipeline with metadata
    save_data = {
        'disease': 'Dengue',
        'pipeline': best_pipeline,
        'model_name': best_model_name,
        'feature_names': list(X.columns),
        'categorical_features': categorical_cols,
        'numerical_features': numerical_cols,
        'target_mapping': {1: 'Positive', 0: 'Negative'},
        'metrics': results_df.iloc[0].to_dict()
    }
    
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(save_data, model_save_path)
    print(f"Successfully saved full pipeline to: {model_save_path}")
    return save_data

if __name__ == '__main__':
    train_dengue_model()
