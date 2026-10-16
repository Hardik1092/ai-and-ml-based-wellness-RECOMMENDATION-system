# Dataset validation — 2026-10-16

Status: **Completed**. Source package: CEP_Synthetic_Data_20000, locally designated
CEP synthetic wellness v1. All source files remain unchanged. SHA-256 manifests,
column types, numeric minima/maxima, missing counts, category frequencies, split
class counts and overlap distances are in [dataset_validation.json](ml_evidence/dataset_validation.json).
No rows, labels or units were changed or silently removed.

| File | Rows | Columns | Missing cells | Duplicate rows |
| --- | --- | --- | --- | --- |
| ..\CEP_Synthetic_Data_20000\cep_ml_features_20000.csv | 20000 | 15 | 0 | 0 |
| ..\CEP_Synthetic_Data_20000\cep_ml_llm_benchmark_cases_200.csv | 200 | 15 | 0 | 0 |
| ..\CEP_Synthetic_Data_20000\cep_synthetic_wellness_20000.csv | 20000 | 15 | 0 | 0 |
| data\cep_ml_features_20000.csv | 20000 | 15 | 0 | 0 |
| C:\Users\ASUS\Desktop\cep my\CEP_Project\ai-ml\data\sample_training_data.csv | 200 | 15 | 0 | 0 |

The engineered CSV is the training input. Its target is wellness_category; the
14 features match FEATURE_NAMES exactly. Raw data are retained as provenance and
to verify feature derivation, never concatenated into engineered training rows.
The raw benchmark is transformed with the same stateless preprocessing and used
only for overlap checks and final benchmarking. IDs, labels and rule outputs are
excluded from model inputs. Existing sample_training_data.csv is preserved.

Every engineered value and target matches the raw package. Regenerating 20,000
profiles with seed 42 reproduces features and labels. Benchmark seed 2026 also
reproduces both. The copied CSV is byte-identical to the package file.

| Category | Count | Percent |
| --- | --- | --- |
| weight_management | 6686 | 33.430% |
| sleep_focus | 5200 | 26.000% |
| hydration_focus | 3326 | 16.630% |
| balanced_wellness | 2183 | 10.915% |
| fitness_improvement | 1755 | 8.775% |
| activity_focus | 850 | 4.250% |

Rules use ordered thresholds for sleep, hydration, activity, BMI and goal. Nominal
7% random relabelling produces **1155 actual changes (5.775%)**,
because random selection can retain the original category. The benchmark contains
13 noisy labels. These are not human annotations.
Features legitimately contain the variables defining the label: this is learning
a synthetic function, not evidence of a causal relationship or wellness benefit.

Stratified seed-42 split: 12,000 train, 4,000 validation, 4,000 test. Row membership
and profile hashes are frozen in [splits.csv](../ai-ml/models/cep-20k-v1/splits.csv).
Exact and near-duplicate counts are zero across all pairs of splits and between
all 20,000 profiles and the benchmark. Near duplicates mean EVERY feature lies
within its documented tolerance (Chebyshev distance <= 1 after dividing by those
tolerances): BMI .1, sleep .1 hours, exercise 1 minute, ratios .01, age .5 years,
and categorical/indicator differences <= .1. This definition is operational, not
a proof that profiles are statistically independent under every possible definition.

All 3,000 legacy generated profiles occur in the 20,000 package. Therefore the old
baseline is historical and must not be claimed to be an independent paired test
of improvement. The new candidate comparison uses one common validation split.

There are 746 profiles younger than 18,
1203 with BMI below 16, and
385 above 40. Values pass broad computational
checks, but the generator includes questionable real-world combinations. No height
column exists to independently verify recorded BMI. Weight, sex and age alone
do not establish medical suitability. These extremes are retained and disclosed;
the data are suitable for engineering demonstration only.

Reproduce from ai-ml/: `.\.venv\Scripts\python.exe -m app.training.validate_dataset --package ../CEP_Synthetic_Data_20000 --dataset data/cep_ml_features_20000.csv --output ../docs/ml_evidence/dataset_validation.json`.
