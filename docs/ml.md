# Machine learning: reproducible local workflow

The ML service predicts one of six general wellness focus categories. All training
and benchmark data in this project are synthetic; scores do not establish clinical
validity. The original model and sample CSV are preserved. The new candidate is
saved separately at `ai-ml/models/cep-20k-v1/` and is **not automatically activated**.
No training occurs during application startup. On 2026-10-16, the candidate was
explicitly activated locally by changing the two artifact paths in `ai-ml/.env`.
See [activation evidence and rollback](ML_ACTIVATION_REPORT.md) and
[unresolved follow-ups](ML_ACTIVATION_FOLLOWUPS.md).

## Reports

- [Baseline audit](CEP_ML_BASELINE_AUDIT.md)
- [Dataset validation](CEP_DATA_VALIDATION_REPORT.md)
- [Training and final evaluation](CEP_ML_TRAINING_REPORT.md)
- [ML/LLM comparison](CEP_ML_LLM_COMPARISON_REPORT.md)
- [Experiment log, safety limits and verification](CEP_ML_EXPERIMENT_LOG.md)

## Commands (PowerShell, from CEP_Project)

Use the existing virtual environment; do not install the package's scikit-learn 1.8.0
artifact. The local project uses scikit-learn 1.6.0. No dependency upgrades are needed.

```powershell
npm run test:ml
npm test
npm run build
Set-Location ai-ml
.\.venv\Scripts\python.exe -m app.training.evaluate --run-dir models/cep-20k-v1
```

To reproduce dataset checks, from `ai-ml/`:

```powershell
.\.venv\Scripts\python.exe -m app.training.validate_dataset --package ../CEP_Synthetic_Data_20000 --dataset data/cep_ml_features_20000.csv --output ../docs/ml_evidence/dataset_validation.json
```

To train a fresh experiment, from `ai-ml/`, choose a NEW output directory each run:

```powershell
.\.venv\Scripts\python.exe -m app.training.train --dataset data/cep_ml_features_20000.csv --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir models/cep-20k-v2 --seed 42
```

The CSV must contain exactly the 14 FEATURE_NAMES columns plus wellness_category.
There is no missing-file fallback, automatic generation or silent filtering. Raw
profiles are not accepted as engineered training data. Training rejects unknown labels,
missing/non-finite values, invalid codes, duplicate profiles and benchmark overlap.
Fixed imputation and feature engineering remain in the existing modules. Scaling for
logistic regression is encapsulated in its fitted sklearn Pipeline. Model selection
uses only validation macro F1. Test membership and data/artifact hashes are saved.

To try the saved candidate locally without editing .env or replacing original files,
from `ai-ml/` (stop another ML process on port 8000 first):

```powershell
$env:MODEL_PATH = 'models/cep-20k-v1/model.pkl'
$env:METADATA_PATH = 'models/cep-20k-v1/feature_metadata.json'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

These variables apply to the current PowerShell session. Remove them or open a new
shell to return to existing .env paths. Do not mix a model with metadata from another
run. Joblib artifacts must come from trusted local sources; loading them executes code.

Benchmark ML and the rule baseline without calling a provider, from `ai-ml/`:

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.benchmark --run-dir models/cep-20k-v1 --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir ../docs/ml_evidence/benchmark-local-v2
```

To run the LLM arm with a benchmark-only model override, append `--llm`
and `--llm-model YOUR_AVAILABLE_MODEL_ID`, using another new output directory.
The runner reads GEMINI_API_KEY and GEMINI_MODEL from process variables or the
existing ignored backend/.env, without printing credentials. The configured
`gemini-1.5-flash` returned HTTP 404. All 200 cases were subsequently attempted with
`gemini-3.5-flash-lite` using a CLI override and unchanged application configuration.
The saved HGB scored 93% accuracy; Gemini scored 81% including invalid/failed cases.
See the [final comparison](CEP_ML_LLM_COMPARISON_REPORT.md) for actual outputs,
failures, retries, timing, estimated cost and methodology limitations. The benchmark
sends only synthetic numeric features, retains every attempt, and supports bounded
technical retries; it never substitutes invented answers.

The [initial runtime verification](ML_RUNTIME_VERIFICATION_REPORT.md) found the
original RF configured and no reachable service. The subsequent authorized
[activation verification](ML_ACTIVATION_REPORT.md) records the new local HGB service
identity and real HTTP recommendation tests. The initial report remains historical.

Regenerate the three measured Markdown reports from the recorded v1 artifacts:

```powershell
# From repository root
.\ai-ml\.venv\Scripts\python.exe scripts/report-ml.py
```

## API compatibility and intentional migration

Prediction (`POST /predict`) accepts the existing `{features: {...}}` or `{raw: {...}}`
objects. Invalid values retain the `{available:false, reason:...}` fallback envelope;
structurally malformed JSON requests return FastAPI 422. Existing camelCase and
snake_case prediction aliases remain. The backend's feature rounding now matches
Python exactly, verified on all 20,000 profiles. Defaults still apply to missing
optional raw log fields; age and BMI remain required. There is no direct-browser
CORS middleware in FastAPI: Express is its server-side caller. Express's configured
frontend-origin allowlist and prediction timeout (default 4 seconds) are retained.

- GET /health, /model/metadata and /model/explanation retain their paths.
- POST /train, /evaluate and /retrain require X-ML-Admin-Token, compared with
  ML_ADMIN_TOKEN. With no configured token they return 503; absent/wrong credentials
  return 403. Do not put this token into frontend code. Keep the service on loopback
  or a trusted network; use transport security if accessed remotely.
- /train requires explicit ML_TRAINING_DATASET and ML_BENCHMARK_DATASET configuration
  and accepts ML_TRAINING_SEED (default 42). Use absolute paths for service configuration.
  It creates a new timestamped run under models/, returns the existing metrics envelope,
  and does not replace the active model. The old samples field remains accepted with
  bounds but does not resize or replace the configured CSV.
- /evaluate now checks the saved dataset/model/split hashes and evaluates the selected
  artifact's frozen test rows. It no longer trains another model. Legacy artifacts
  lack that provenance and return an unavailable explanation.
- /retrain retains its route but returns available:false/promoted:false even with
  authorization. Positive feedback is not an independently validated target and can
  amplify earlier model errors. Force no longer bypasses this restriction.
- Express POST /api/ml/retrain additionally requires authentication AND a user ID
  in ML_ADMIN_USER_IDS (comma-separated, default empty). Its outbound service token
  comes from backend ML_ADMIN_TOKEN. Existing UI users see the normal error handling
  if they are not administrators. Prediction access is unaffected.

The old no-argument `python -m app.training.train` command now errors with explicit
required arguments. The historical Python `train()` function remains for the original
baseline tests; it does not silently ingest the new CSV. Package export_dataset.py
instructions describe a file absent from this checkout; use the commands above.
