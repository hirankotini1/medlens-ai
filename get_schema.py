import pandas as pd
import json

datasets = {
    'anemia': 'disease_prediction/datasets/anemia_clean.csv',
    'dengue': 'disease_prediction/datasets/dengue_clean.csv',
    'liver': 'disease_prediction/datasets/liver_clean.csv',
    'thyroid': 'disease_prediction/datasets/thyroid_clean.csv'
}

schema = {}
for name, path in datasets.items():
    df = pd.read_csv(path)
    schema[name] = {
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'null_counts': {col: int(cnt) for col, cnt in df.isnull().sum().items() if cnt > 0},
        'sample_row': df.iloc[0].to_dict()
    }

with open('detected_schemas.json', 'w') as f:
    json.dump(schema, f, indent=2)

print("Schema generated successfully:")
print(json.dumps(schema, indent=2))
