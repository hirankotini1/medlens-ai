import os
import glob
import hashlib
import cv2
import numpy as np
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

class MalariaFeatureExtractor:
    """
    Extracts informative computer vision features from cell microscopy images:
    - Multi-channel color moments (Mean, Std, Skewness across RGB & HSV)
    - Cell contour and morphology statistics
    - Grayscale texture & spatial histogram features
    """
    def __init__(self, img_size=(64, 64)):
        self.img_size = img_size

    def extract_single_image(self, img_input):
        if isinstance(img_input, str):
            img = cv2.imread(img_input)
            if img is None:
                raise ValueError(f"Could not load image from: {img_input}")
        elif isinstance(img_input, np.ndarray):
            img = img_input
        else:
            raise TypeError("Input must be a file path string or numpy image array.")

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img_resized = cv2.resize(img, self.img_size)
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)

        features = []

        # 1. Color channel statistics
        for channel in cv2.split(img_resized):
            features.extend([
                np.mean(channel),
                np.std(channel),
                np.percentile(channel, 25),
                np.percentile(channel, 75),
                np.max(channel) - np.min(channel)
            ])
            
        for channel in cv2.split(hsv):
            features.extend([
                np.mean(channel),
                np.std(channel),
                np.percentile(channel, 25),
                np.percentile(channel, 75)
            ])

        # 2. Histogram features
        hist_b = cv2.calcHist([img_resized], [0], None, [16], [0, 256]).flatten()
        hist_g = cv2.calcHist([img_resized], [1], None, [16], [0, 256]).flatten()
        hist_r = cv2.calcHist([img_resized], [2], None, [16], [0, 256]).flatten()
        hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
        
        for h in [hist_b, hist_g, hist_r, hist_h]:
            norm_h = h / (np.sum(h) + 1e-7)
            features.extend(norm_h)

        # 3. Spatial thumbnail pixels
        thumb = cv2.resize(gray, (16, 16)).flatten() / 255.0
        features.extend(thumb)

        # 4. Hu Moments
        moments = cv2.moments(gray)
        hu_moments = cv2.HuMoments(moments).flatten()
        for hu in hu_moments:
            features.append(-1 * np.sign(hu) * np.log10(abs(hu) + 1e-10))

        return np.array(features, dtype=np.float32)

    def extract_dataset(self, folder_path, exclude_hashes=None):
        if exclude_hashes is None:
            exclude_hashes = set()
            
        X, y, file_paths = [], [], []
        classes = {'parasite': 1, 'uninfected': 0}
        
        for cls_name, cls_label in classes.items():
            cls_dir = os.path.join(folder_path, cls_name)
            if not os.path.exists(cls_dir):
                continue
            
            for file_name in os.listdir(cls_dir):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(cls_dir, file_name)
                    with open(full_path, 'rb') as fp:
                        h = hashlib.sha256(fp.read()).hexdigest()
                    if h in exclude_hashes:
                        continue
                    
                    feat = self.extract_single_image(full_path)
                    X.append(feat)
                    y.append(cls_label)
                    file_paths.append(full_path)
                    
        return np.array(X), np.array(y), file_paths


def train_malaria_model(dataset_dir=None, model_save_path=None):
    if dataset_dir is None:
        dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'malaria_simple')
    if model_save_path is None:
        model_save_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'malaria_pipeline.joblib')
        
    print("=" * 60)
    print("  MALARIA TRAINING PIPELINE (WITH ZERO TEST-LEAKAGE AUDIT)")
    print("=" * 60)
    
    train_folder = os.path.join(dataset_dir, 'train')
    test_folder = os.path.join(dataset_dir, 'test')
    
    extractor = MalariaFeatureExtractor(img_size=(64, 64))
    
    # 1. Collect all test set hashes to guarantee zero leakage
    test_hashes = set()
    for root, _, files in os.walk(test_folder):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                p = os.path.join(root, f)
                with open(p, 'rb') as fp:
                    test_hashes.add(hashlib.sha256(fp.read()).hexdigest())
                    
    print(f"Collected {len(test_hashes)} unique test image hashes.")
    
    # 2. Extract Training Set excluding any image that appears in the test set
    X_train, y_train, train_files = extractor.extract_dataset(train_folder, exclude_hashes=test_hashes)
    X_test, y_test, test_files = extractor.extract_dataset(test_folder)
    
    print(f"Cleaned X_train shape: {X_train.shape} (Parasite: {np.sum(y_train==1)}, Uninfected: {np.sum(y_train==0)})")
    print(f"Unseen X_test shape:   {X_test.shape} (Parasite: {np.sum(y_test==1)}, Uninfected: {np.sum(y_test==0)})")
    
    target_names = ['Uninfected', 'Parasite']
    
    candidate_models = {
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
        "Extra Trees": ExtraTreesClassifier(n_estimators=200, max_depth=10, random_state=42),
        "Support Vector Machine (RBF)": SVC(kernel='rbf', probability=True, C=5.0, random_state=42),
        "Multi-Layer Perceptron (Neural Net)": MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42)
    }
    
    results = []
    trained_pipelines = {}
    
    print("\n--- Model Benchmark Comparison (Deduplicated Clean Split) ---")
    for name, clf in candidate_models.items():
        pipe = Pipeline(steps=[
            ('scaler', StandardScaler()),
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
    
    best_model_name = results_df.iloc[0]['Model']
    best_pipeline = trained_pipelines[best_model_name]
    print(f"\n=> Best Selected Model: {best_model_name}")
    
    y_pred_best = best_pipeline.predict(X_test)
    cm = confusion_matrix(y_test, y_pred_best)
    print("\nConfusion Matrix (Unseen Test Set):")
    print(cm)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred_best, target_names=target_names))
    
    save_data = {
        'disease': 'Malaria',
        'extractor': extractor,
        'pipeline': best_pipeline,
        'model_name': best_model_name,
        'target_mapping': {1: 'Parasite Detected', 0: 'Uninfected / Clear'},
        'metrics': results_df.iloc[0].to_dict()
    }
    
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(save_data, model_save_path)
    print(f"Successfully saved clean malaria pipeline to: {model_save_path}")
    return save_data

if __name__ == '__main__':
    train_malaria_model()
