# ML training and evaluation — 2026-10-16

Status: **Completed**. No dependency was installed or upgraded. Models trained in
the project's Python 3.13.5 environment, scikit-learn 1.6.0. Full package versions:
[python_environment.json](ml_evidence/python_environment.json). Installed JS versions:
[backend](ml_evidence/backend_dependencies.json), [frontend](ml_evidence/frontend_dependencies.json).
Node is 22.17.1. npm reported an existing extraneous wellness-system local package
in both node_modules directories; no dependency cleanup was performed.

Historical original trainer: 3,000 generated rows, seed 42, 2,400/600 stratified
train/test, fixed imputation and feature engineering. Original sample CSV was not
used by that trainer. This was executed before changes without saving artifacts.
Accuracy 0.901667 (rounded API value 0.9017), weighted precision 0.899992,
weighted recall 0.901667, weighted F1 0.898442, macro F1 0.846610.
Full baseline confusion/per-class metrics and time are in
[original_baseline.json](ml_evidence/original_baseline.json).

New experiment: explicit 20,000-row engineered CSV, seed 42, 60/20/20 stratified
split. All four candidates see exactly the same train and validation rows. Selection
uses validation macro F1 alone, with fixed parameters and no benchmark tuning.
Dummy is a minimum baseline; logistic regression tests a linear boundary; the
original Random Forest is retained as a candidate; histogram gradient boosting
tests nonlinear thresholds with the existing sklearn dependency. StandardScaler
is fitted on training rows only, inside the logistic pipeline. Other preprocessing
is the existing stateless feature contract. No feature selection was performed.

## Candidate comparison — validation only

| Candidate | Accuracy | Macro F1 | Weighted F1 | Train seconds | Predict p50 ms | Serialized bytes |
| --- | --- | --- | --- | --- | --- | --- |
| dummy | 0.3342 | 0.083505 | 0.167469 | 0.0031 | 0.0240 | 1447 |
| logistic_regression | 0.6797 | 0.506405 | 0.632073 | 0.0694 | 0.5610 | 3273 |
| random_forest | 0.9247 | 0.890720 | 0.923620 | 2.5685 | 5.6831 | 27258105 |
| hist_gradient_boosting | 0.9437 | 0.923581 | 0.942997 | 1.5809 | 14.9586 | 1632512 |

Selected **hist_gradient_boosting**: 150 iterations, 15 maximum leaves, L2=1,
early stopping disabled, seed 42. It achieved higher validation macro F1 and a
smaller artifact than Random Forest, but was slower per prediction on this machine
and does not expose impurity feature importances. No claim of universal superiority.
The fitted 12,000-row candidate was saved without refitting, so the deployed candidate
is exactly the one tested. The 4,000 test rows were accessed only after selection.
Subsequent evaluation/reload checks reproduce the same frozen result, not new tuning.

## Final held-out test

| Metric | Value |
| --- | --- |
| accuracy | 0.936300 |
| precision | 0.936200 |
| recall | 0.936300 |
| macro_f1 | 0.911188 |
| weighted_f1 | 0.935277 |
| log_loss | 0.361521 |
| multiclass_brier | 0.122634 |

Accuracy is exactly 3745/4000 = 93.625%; compatibility fields round to four decimals.

| Category | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| activity_focus | 0.939850 | 0.735294 | 0.825083 | 170 |
| balanced_wellness | 0.927059 | 0.901602 | 0.914153 | 437 |
| fitness_improvement | 0.930380 | 0.837607 | 0.881559 | 351 |
| hydration_focus | 0.938438 | 0.939850 | 0.939144 | 665 |
| sleep_focus | 0.937442 | 0.965385 | 0.951208 | 1040 |
| weight_management | 0.938085 | 0.974570 | 0.955979 | 1337 |

Confusion matrix: rows reference, columns predicted, in the order below.

| Reference / predicted | activity_focus | balanced_wellness | fitness_improvement | hydration_focus | sleep_focus | weight_management |
| --- | --- | --- | --- | --- | --- | --- |
| activity_focus | 125 | 1 | 5 | 6 | 11 | 22 |
| balanced_wellness | 0 | 394 | 7 | 7 | 11 | 18 |
| fitness_improvement | 3 | 8 | 294 | 10 | 24 | 12 |
| hydration_focus | 1 | 5 | 1 | 625 | 13 | 20 |
| sleep_focus | 3 | 7 | 3 | 9 | 1004 | 14 |
| weight_management | 1 | 10 | 6 | 9 | 8 | 1303 |

Probabilities are uncalibrated. Multiclass Brier is mean(sum((p-one_hot)^2)), without
division by the number of classes; log loss is multiclass cross entropy. No separate
calibrator was fitted. Lower probability losses do not establish medical confidence.
Latency uses 100 individual validation predictions after warmup, excluding HTTP and
preprocessing. Single-machine timing varies with load/thread scheduling. Candidate
model sizes are serialized in-memory joblib bytes. Full params, validation per-class
metrics, p95 latency and losses: [experiment.json](../ai-ml/models/cep-20k-v1/experiment.json).

The saved candidate is [models/cep-20k-v1/model.pkl](../ai-ml/models/cep-20k-v1/model.pkl),
with metadata, frozen split membership and per-example test predictions beside it.
Checksums protect model, source dataset and split records. Original artifacts and
datasets remain unchanged; automatic activation was not performed. Existing .env
still selects the original model until the documented MODEL_PATH/METADATA_PATH overrides
are used. Model loading verifies feature order, category vocabulary, checksum and
sklearn version for the new artifact, while retaining the original filename fallback.

Python/Node parity testing exposed different rounding at half-way values. Backend
feature rounding now matches Python's IEEE-754 ties-to-even semantics; all 20,000
profiles agree within 1e-9. Training data and Python feature formulas were unchanged.
The API was tested with the actual saved candidate, missing models, malformed/raw
inputs and extreme valid profiles. Robustness here means finite schema-compliant
outputs, not trustworthy advice outside the training distribution.

Known runtime warnings: deprecated AnyIO portal alias in Starlette; sklearn/SciPy
unknown `iprint` optimizer option; unavailable Windows `wmic` physical-core detection
(joblib uses logical cores). These did not prevent training or evaluation. No package
upgrade was performed to hide them. No plot library is installed; tables provide
candidate, class and confusion-matrix comparisons without adding dependencies.

Exact reproduction and activation commands are in [docs/ml.md](ml.md).
