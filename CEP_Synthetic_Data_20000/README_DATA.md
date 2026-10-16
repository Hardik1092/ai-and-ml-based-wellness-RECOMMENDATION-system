# CEP synthetic data package

Generated reproducibly with seed 42. All records are synthetic.

## Files
- `cep_synthetic_wellness_20000.csv`: 20,000 raw synthetic wellness profiles with target label.
- `cep_ml_features_20000.csv`: 20,000 rows with engineered model features and target label.
- `cep_ml_llm_benchmark_cases_200.csv`: 200 synthetic profiles for running both recommenders on the same inputs.
- `cep_synthetic_wellness_20000.metadata.json`: dataset schema and class counts.
- `ML_LLM_COMPARISON_PLAN.md`: evaluation protocol for ML vs LLM.
- `ML_TRAINING_REPORT.md`: training notes from the project package.
- `DATA_VALIDATION_REPORT.json`: basic structural checks and label distribution.

## Use
Use the engineered-feature CSV to inspect the model's expected feature/label schema. For reproducible training, run the generator and training pipeline from the full project package in its configured Python environment.

## Important limitation
This is synthetic, rule-labelled data for software development and pipeline testing. It does not establish medical accuracy, clinical validity, or performance on real users. The 200 benchmark cases are synthetic and should not be described as an independent real-world test set.
