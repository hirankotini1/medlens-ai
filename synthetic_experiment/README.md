# Synthetic Data Experiment

This directory houses the controlled synthetic data generation, augmentation training, cross-validation, and audit benchmarking for the 4 tabular disease pipelines.

## Directory Structure
- `generate_anemia.py`: Generates 25%, 50%, 100% synthetic Anemia data from the training split only.
- `generate_dengue.py`: Generates 25%, 50%, 100% synthetic Dengue data from the training split only.
- `generate_liver.py`: Generates 25%, 50%, 100% synthetic Liver data from the training split only.
- `generate_thyroid.py`: Generates 25%, 50%, 100% synthetic Thyroid data from the training split only.
- `generated_data/`: Contains all generated synthetic CSV files.
- `train_augmented.py`: Training engine evaluating 0%, 25%, 50%, 100% augmentation with strictly in-fold 5-fold CV.
- `compare_models.py`: Complete execution and report generator.
- `results/`:
  - `comparison.csv`: Full metric results across all diseases and augmentation tiers.
  - `report.md`: Detailed audit report.
  - `plots/`: Comparison charts for Holdout accuracy, F1-scores, and CV distributions.
