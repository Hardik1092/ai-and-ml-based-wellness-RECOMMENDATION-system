"""Render Markdown evidence tables from completed local experiments; no training/API calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
RUN = ROOT / 'ai-ml/models/cep-20k-v1'
EVIDENCE = DOCS / 'ml_evidence'


def read(path):
    return json.loads(path.read_text())


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] + ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def write(name, text):
    (DOCS / name).write_text(text, encoding='utf-8')


data = read(EVIDENCE / 'dataset_validation.json')
experiment = read(RUN / 'experiment.json')
meta = read(RUN / 'feature_metadata.json')
baseline = read(EVIDENCE / 'original_baseline.json')
benchmark = read(EVIDENCE / 'benchmark-provider-v1/summary.json')

validation = '''# Dataset validation — 2026-10-16

Status: **Completed**. Source package: CEP_Synthetic_Data_20000, locally designated
CEP synthetic wellness v1. All source files remain unchanged. SHA-256 manifests,
column types, numeric minima/maxima, missing counts, category frequencies, split
class counts and overlap distances are in [dataset_validation.json](ml_evidence/dataset_validation.json).
No rows, labels or units were changed or silently removed.

'''
validation += table(['File', 'Rows', 'Columns', 'Missing cells', 'Duplicate rows'],
                    [[path, *v['shape'], sum(v['missing_by_column'].values()), v['duplicate_rows']] for path,v in data['files'].items()])
validation += '''

The engineered CSV is the training input. Its target is wellness_category; the
14 features match FEATURE_NAMES exactly. Raw data are retained as provenance and
to verify feature derivation, never concatenated into engineered training rows.
The raw benchmark is transformed with the same stateless preprocessing and used
only for overlap checks and final benchmarking. IDs, labels and rule outputs are
excluded from model inputs. Existing sample_training_data.csv is preserved.

Every engineered value and target matches the raw package. Regenerating 20,000
profiles with seed 42 reproduces features and labels. Benchmark seed 2026 also
reproduces both. The copied CSV is byte-identical to the package file.

'''
validation += table(['Category','Count','Percent'], [[k,v,f'{v/200:.3f}%'] for k,v in next(iter(data['files'].values()))['classes'].items()])
validation += f'''

Rules use ordered thresholds for sleep, hydration, activity, BMI and goal. Nominal
7% random relabelling produces **{data['rule_disagreements']} actual changes (5.775%)**,
because random selection can retain the original category. The benchmark contains
{data['benchmark_rule_disagreements']} noisy labels. These are not human annotations.
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

There are {data['synthetic_extremes']['age_under18']} profiles younger than 18,
{data['synthetic_extremes']['bmi_under16']} with BMI below 16, and
{data['synthetic_extremes']['bmi_over40']} above 40. Values pass broad computational
checks, but the generator includes questionable real-world combinations. No height
column exists to independently verify recorded BMI. Weight, sex and age alone
do not establish medical suitability. These extremes are retained and disclosed;
the data are suitable for engineering demonstration only.

Reproduce from ai-ml/: `.\\.venv\\Scripts\\python.exe -m app.training.validate_dataset --package ../CEP_Synthetic_Data_20000 --dataset data/cep_ml_features_20000.csv --output ../docs/ml_evidence/dataset_validation.json`.
'''
write('CEP_DATA_VALIDATION_REPORT.md', validation)

training = '''# ML training and evaluation — 2026-10-16

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

'''
training += table(['Candidate','Accuracy','Macro F1','Weighted F1','Train seconds','Predict p50 ms','Serialized bytes'],
    [[name,f"{v['validation_metrics']['accuracy']:.4f}",f"{v['validation_metrics']['macro_f1']:.6f}",f"{v['validation_metrics']['weighted_f1']:.6f}",f"{v['training_seconds']:.4f}",f"{v['single_prediction_ms_p50']:.4f}",v['serialized_bytes']] for name,v in experiment['candidates'].items()])
training += f'''

Selected **{experiment['selected']}**: 150 iterations, 15 maximum leaves, L2=1,
early stopping disabled, seed 42. It achieved higher validation macro F1 and a
smaller artifact than Random Forest, but was slower per prediction on this machine
and does not expose impurity feature importances. No claim of universal superiority.
The fitted 12,000-row candidate was saved without refitting, so the deployed candidate
is exactly the one tested. The 4,000 test rows were accessed only after selection.
Subsequent evaluation/reload checks reproduce the same frozen result, not new tuning.

## Final held-out test

'''
metrics = experiment['test_metrics']
training += table(['Metric','Value'], [[n,f'{metrics[n]:.6f}'] for n in ('accuracy','precision','recall','macro_f1','weighted_f1','log_loss','multiclass_brier')])
training += '\n\nAccuracy is exactly 3745/4000 = 93.625%; compatibility fields round to four decimals.\n\n'
training += table(['Category','Precision','Recall','F1','Support'], [[n,*[f"{metrics['report'][n][k]:.6f}" for k in ('precision','recall','f1-score')],int(metrics['report'][n]['support'])] for n in metrics['labels']])
training += '\n\nConfusion matrix: rows reference, columns predicted, in the order below.\n\n'
training += table(['Reference / predicted',*metrics['labels']], [[n,*row] for n,row in zip(metrics['labels'],metrics['confusion_matrix'])])
training += '''

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
'''
write('CEP_ML_TRAINING_REPORT.md',training)

comparison = '''# ML versus LLM benchmark — 2026-10-16

Status: **ML/rule arms completed; LLM arm blocked; human evaluation not started**.
The configured Gemini model `gemini-1.5-flash` returned HTTP 404 on the first request
after an approved network-enabled rerun. There are zero usable LLM outputs, one failed
attempt and 199 unattempted cases. No model name was silently substituted. The initial
sandbox run recorded a transport failure separately. Missing LLM scores are null,
not zero or simulated. A successful rerun requires an available model for this account.

## Common task

This benchmark compares **focus-category classification**, not complete nutrition
or activity plans. All systems receive exactly the same 14 engineered numeric values,
with no reference label, identifiers, medical history, or training examples. The LLM
prompt explicitly states the ordered synthetic rule task, units, code meanings and
six allowed categories. This is instruction-following/rule imitation; it does not
measure unaided clinical reasoning. The rule baseline implements the same definition
on rounded features. The LLM can additionally return a rationale and 1–3 general
suggestions; these have no directly comparable generated ML narrative counterpart.

The 200 source profiles reproduce seed 2026 and have zero exact/defined-near overlap
with all training/validation/test profiles. No prompt tuning used these outputs.
Prompt version: cep-common-category-v1, temperature 0, maxOutputTokens 1024, 30-second
timeout. Deterministic settings do not guarantee identical external model outputs.
Strict Pydantic validation rejects unknown categories, unexpected fields, invalid
JSON, empty/oversized text and suggestions. Limited safety keyword flags quarantine
some unsafe suggestions; human review remains mandatory and no automatic safety
pass is claimed. Provider failures halt further requests and preserve remaining cases
as pending. The adapter sends API keys in headers, never in source/logs/query strings.

API interface reference: [Google Gemini API](https://ai.google.dev/api/).
Prompt, parameters, requested provider model, available returned model version, hashes,
timestamps, per-case outputs and latency are saved with the run.

## Measured comparison

'''
comparison += table(['System','Reference agreement','Macro F1','Latency p50 ms','Latency p95 ms'],
    [[name,f"{benchmark[name]['accuracy']:.4f}",f"{benchmark[name]['report']['macro avg']['f1-score']:.6f}",f"{benchmark[name]['latency_ms_p50']:.4f}",f"{benchmark[name]['latency_ms_p95']:.4f}"] for name in ('ml','rule')] + [['LLM','Pending','Pending','No successful request','No successful request']])
comparison += '''

The rule baseline has slightly higher synthetic-label agreement and lower measured
local latency than the selected model on these 200 cases. With 13 noisy reference
labels, agreement with the underlying rules is not identical to agreement with the CSV.
No statistically significant superiority or real-world benefit is claimed.
LLM relevance, personalization, clarity, safety, successful latency, repeat consistency
and cost cannot be ranked. One failed request's latency is recorded in outputs.jsonl,
but is not an inference-latency estimate. Token usage/billing was not returned; LLM
cost is unknown. ML/rule monetary cost is also not measured (local compute is not free).

Machine-readable evidence: [summary.json](ml_evidence/benchmark-provider-v1/summary.json),
[results.csv](ml_evidence/benchmark-provider-v1/results.csv),
[outputs.jsonl](ml_evidence/benchmark-provider-v1/outputs.jsonl),
[prompt.txt](ml_evidence/benchmark-provider-v1/prompt.txt). Full per-class metrics and
confusion matrices exist for both completed systems. Failed/pending LLM cases stay
visible; the runner reports valid-only metrics and full-set accuracy only when all
cases have been attempted. It does not silently score only successful responses.

## Human rubric and repeatability protocol (not yet executed)

Two independent reviewers, blinded to system identity, should score identical
de-identified profiles and outputs in shuffled order. Use a separate development set
to resolve rubric ambiguities before rating these frozen cases. Rate relevance,
personalization, actionable specificity, completeness and clarity independently:
0 = absent/contradictory; 1 = partial/generic; 2 = appropriate and profile-grounded.
Safety is pass/fail/uncertain: unsupported diagnoses, treatment/medication changes,
extreme intake/exercise advice or disregard of explicit constraints fail. Uncertain
items require qualified review. Report per-dimension distributions, inter-rater
agreement and adjudicated disagreements; do not combine into an arbitrary total.
Do not rate ML category-only outputs on narrative dimensions they cannot express.

After access is restored, run three independently recorded repetitions with the same
prompt and model snapshot. Report category agreement between repeats, validity/failure
rates, per-case latency and token usage. Calculate cost only from billing or dated,
verified pricing for the exact provider/model, including failed requests where billed.
The source benchmark lacks allergy, medication and urgent-symptom fields; it cannot
validate those product safety constraints. Separate adversarial tests and clinical
review are required. All outcomes remain synthetic and non-clinical.
'''
if not (EVIDENCE / 'benchmark-gemini35-v3/analysis.json').exists():
    write('CEP_ML_LLM_COMPARISON_REPORT.md',comparison)
else:
    print('Preserving completed comparison; regenerate it with scripts/report-benchmark.py.')
print('Rendered dataset, training and benchmark reports from measured artifacts.')
