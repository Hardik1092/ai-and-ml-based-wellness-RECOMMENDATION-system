# CEP Project — Synthetic ML Training Report

## Run configuration

- Generated rows: **20,000**
- Random seed: **42**
- Model: `RandomForestClassifier`
- Holdout fraction: **20%** (4,000 rows)
- Labels: existing rule-based `label_row()` with configured 7% label noise
- Input: 14 features from the existing `FEATURE_NAMES` list

## Observed holdout metrics

These metrics were obtained by running the project's training function in the working environment:

| Metric | Result |
|---|---:|
| Accuracy | 0.9157 |
| Weighted precision | 0.9194 |
| Weighted recall | 0.9157 |
| Weighted F1 | 0.9144 |

## Critical interpretation

These scores measure how well the Random Forest reproduces the project's **synthetic rule-generated labels** on a random holdout from the same synthetic generator. They do **not** measure medical validity, effectiveness for real users, or generalization to real-world populations. The current labels are derived from `label_row()` and include artificial label noise, so high metrics can largely reflect learning the rule system.

The model artifact was not bundled because it was trained in a runtime with scikit-learn 1.8.0 while the project's `requirements.txt` pins scikit-learn 1.6.0. Retrain inside the project's own virtual environment before using the model artifact locally.

## Generated files

- `ai-ml/data/cep_synthetic_wellness_20000.csv` — raw synthetic profiles and labels.
- `ai-ml/data/cep_ml_features_20000.csv` — engineered model features and labels.
- `ai-ml/data/cep_synthetic_wellness_20000.metadata.json` — seed, class counts, schema, and limitations.
- `ai-ml/data/cep_ml_llm_benchmark_cases_200.csv` — separate synthetic benchmark profiles generated with seed `2026`; not part of the 20,000-row training run.

The 200 benchmark cases are for repeatable side-by-side output review. For a valid comparison, run both systems on the same cases and record latency, failure rate, relevance, specificity, goal consistency, explanation quality, and safety-constraint adherence. Do not treat the synthetic target labels as a human quality rating of LLM text.
