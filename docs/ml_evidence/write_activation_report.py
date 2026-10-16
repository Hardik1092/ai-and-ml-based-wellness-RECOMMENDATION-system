import hashlib,json
from pathlib import Path
E=Path(__file__).parent;ROOT=E.parents[1]
read=lambda f:json.loads((E/f).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a,b,c=read('activation_api.json'),read('activation_backend.json'),read('activation_config.json')
identity=a['identity'];listener=read('activation_listener.json')
if isinstance(listener,list):listener=listener[0]
assert listener['OwningProcess']==identity['pid']
original=read('original_files.json');oldconfig=read('gemini-diagnostic-live.json')['configuration_hashes_before']
unchanged={p:sha(ROOT/p)==h for p,h in original.items()}
otherconfig={p:sha(ROOT/p)==h for p,h in oldconfig.items() if p!='ai-ml\\.env'}
raw=(ROOT/'ai-ml/.env').read_bytes()
reverse=raw.replace(b'MODEL_PATH=models/cep-20k-v1/model.pkl',b'MODEL_PATH=models/model.pkl').replace(b'METADATA_PATH=models/cep-20k-v1/feature_metadata.json',b'METADATA_PATH=models/feature_metadata.json')
assert hashlib.sha256(reverse).hexdigest()==c['before_sha256']
assert all(unchanged.values()) and all(otherconfig.values())
assert sha(ROOT/'ai-ml/models/cep-20k-v1/model.pkl')==identity['model_sha256']
integrity={'original_files_unchanged':unchanged,'other_configuration_unchanged':otherconfig,'only_two_env_setting_changes':True,'rollback_reconstructs_original_env_bytes':True,'active_env_sha256':sha(ROOT/'ai-ml/.env'),'candidate_sha256':identity['model_sha256'],'listener_matches_attested_pid':True}
(E/'activation_integrity.json').write_text(json.dumps(integrity,indent=2))
report=f'''# Local ML activation report — 2026-10-16

**PASS: `cep-20k-v1` (HistGradientBoostingClassifier) is activated and verified in the local HTTP service.** This supersedes the activation/availability findings in the historical [initial verification report](ML_RUNTIME_VERIFICATION_REPORT.md); its preprocessing and LLM safety findings remain open.

## Minimal activation change

Only application configuration file `ai-ml/.env` changed, and only these two settings:

```dotenv
MODEL_PATH=models/cep-20k-v1/model.pkl
METADATA_PATH=models/cep-20k-v1/feature_metadata.json
```

Previous values were `models/model.pkl` and `models/feature_metadata.json`. No application source, dependency, training artifact or preprocessing behavior was changed. All 13 original preserved files still match their hashes. Original Random Forest SHA-256: `9c5d7598ba2b33ad1155d1780b6021dd923f8fcc34bfe250236246ce3453c29c`. Backend configuration and credentials are unchanged; no keys were printed. Restoring only the two previous setting lines reconstructs the original `.env` bytes exactly (verified by SHA-256).

## Compatibility gate before activation

The preflight loaded the saved candidate without fitting it, checked its checksum against recorded metadata, confirmed scikit-learn 1.6.0, exact ordered `feature_names_in_`, all six expected classes, and predictions/probability vectors on 11 backend-generated synthetic profiles. The inputs still match the earlier cross-language preprocessing audit. The existing loader/API already supports HGB; no inference code adaptation is necessary. Raw/backend feature parity also passed the regression tests.

Ordered features: {', '.join(identity['features'])}.

Classes: {', '.join(identity['classes'])}.

Preprocessing remains the existing unscaled 14-feature engineering, imputation, encoding and validation pipeline. Returned probability maps, camelCase/snake_case aliases, labels and unavailable envelope remain compatible. No clinical confidence interpretation is made.

## Runtime identity evidence

- URL: `http://127.0.0.1:8000`
- Serving PID at verification: **{identity['pid']}**; TCP port owner independently matched this PID.
- Load time: `{identity['loaded_at_utc']}`.
- Resolved model: `{identity['resolved_model_path']}`.
- Resolved metadata: `{identity['resolved_metadata_path']}`.
- Actual loaded Python type: `{identity['actual_model_type']}`.
- SHA-256: `{identity['model_sha256']}`.

The verification launcher imports the unchanged FastAPI app, calls its unchanged loader, checks the disk checksum before/after loading against metadata, and records the actual cached object type/path/features in the same process that serves Uvicorn. One worker, no reload, loopback only. The loaded object remains the one used by `/predict`. This evidence is stronger than reading a configured path or metadata label alone. The ordinary metadata endpoint itself has not been extended with path attestation.

`GET /health` and `/model/metadata` returned HTTP 200. All 11 synthetic `/predict` calls returned available HGB predictions with probability vectors exactly matching direct inference from the candidate. An additional raw-input request returned sleep_focus; a repeated baseline was identical; a deliberately incomplete request returned HTTP 200/available:false as designed. There were no failed valid ML requests. Existing joblib physical-core discovery falls back to logical cores, with a warning; this did not interrupt service.

| Synthetic intervention | Class | Maximum probability |
| --- | --- | --- |
'''
for row in a['rows']:report+=f"| {row['id']} | {row['prediction']['category']} | {row['prediction']['confidence']} |\n"
report+='''
Changing sleep from 8 to 7 h keeps balanced_wellness but changes probability from 0.9791 to 0.9718. Zero exercise alone keeps balanced_wellness (0.9613); lowering steps next to 1000 changes it to activity_focus (0.9916). The low-movement case changes only steps relative to the zero-exercise case. Goal/weight/age changes recompute dependent engineered metrics rather than pretending to change just one feature column.

## Real backend HTTP and recommendation verification

The verification process started the unchanged Express app on a loopback ephemeral port with a fresh MongoMemoryServer, seeded 58 foods/28 activities there, and created a synthetic account. Requests used real HTTP, authentication cookies, profile/log controllers, model inference over HTTP, recommendation ranking and storage. **No ML prediction stub was used.** Only this disposable process disabled external LLM calls so the hybrid path could be isolated without external transmission. No production MongoDB connection or data mutation occurred. The temporary backend/database were stopped after verification; the local ML service remains running.

Eight scenarios passed the nutrition and activity APIs. Profile goal general_wellness→improve_fitness changed the prediction to fitness_improvement (0.9145) and produced strength/cardio/jogging recommendations. Sleep 8→5 h changed breakfast from Moong Dal Chilla + Idli with Sambar to Moong Dal Chilla + Masala Oats, and dinner replaced Vegetable Khichdi with Palak Dal. Water reduced to 800 ml produced hydration_focus and Sprouts Salad + Soy Milk Smoothie for breakfast.

Low movement produced Evening Stroll, Hip and Shoulder Mobility, Sun Salutations. A same-profile/same-log control with ML disabled only in the disposable backend process instead produced Evening Stroll, Sun Salutations, Full Body Stretch. This controls for other rule changes and demonstrates the category's downstream activity effect. Nutrition/category fields and bonuses were recorded for every response. A vegan profile with eight allergy exclusions passed catalog checks.

One unchanged result is explained by input precedence: updating profile sleep to 5 h while posting `sleep:null` to an existing daily log retains its earlier 8 h value. The log response confirms 8 h; the model correctly continues receiving that value. The log update handler skips nulls and logged sleep takes precedence. This is distinct from the unresolved zero-value bug.

No browser interaction was performed. Rendering is supported by the prior source trace but live browser rendering and any production/remote deployment remain NOT VERIFIED. External LLM dietary compliance was not tested or fixed.

## Regression results

- Python: **28 passed, 13 deselected**, 2.95 s. All fitting/retraining tests deliberately excluded. Warnings: existing Starlette/AnyIO deprecation and joblib physical-core discovery fallback.
- Backend: **51 passed, 6 suites**, 9.559 s, isolated database. The existing regressions use an ML fixture; the separate real HTTP verification above covers the activated artifact.
- Live ML: **11/11 profile vectors** match the saved candidate; raw input, repeat consistency and invalid-input envelope also passed.
- Backend live integration: **8 scenarios × nutrition/activity**, plus rules-only activity control passed. The initial seven-scenario run is preserved separately.
- Integrity: originals/candidate preserved, only the two authorized `.env` setting values changed; reverse replacement verified against the original `.env` hash.

## Rollback

The original model and metadata remain in place. First stop the serving process deliberately after rechecking that PID 1824 still owns this verification service (PIDs may be reused). The attestation is in `activation_runtime.json`; inspect the port owner before stopping it. Then, from the repository root:

```powershell
.\\ai-ml\\.venv\\Scripts\\python.exe docs/ml_evidence/activation_control.py rollback
npm run dev:ml
```

Rollback changes only MODEL_PATH and METADATA_PATH back to the original values and refuses to overwrite unexpected current settings. Restart is necessary because the loader caches its model. Do not use the candidate-only `serve_verified_model.py` launcher for RF rollback: it deliberately asserts the HGB identity. Rollback was verified as an exact inverse of the config edit but was not applied to the running service. After rollback, verify the RF metadata/API again. To stop the current service now, recheck its recorded PID and loopback listener ownership before `Stop-Process -Id 1824`.

## Exact execution commands

From repository root unless noted:

```powershell
.\\ai-ml\\.venv\\Scripts\\python.exe docs/ml_evidence/activation_control.py check
.\\ai-ml\\.venv\\Scripts\\python.exe docs/ml_evidence/activation_control.py activate
# Actual service launch: hidden process with stdout/stderr saved below.
$activationRoot = (Get-Location).Path
$activationPython = Join-Path $activationRoot 'ai-ml\\.venv\\Scripts\\python.exe'
$activationScript = Join-Path $activationRoot 'docs\\ml_evidence\\serve_verified_model.py'
$activationProcess = Start-Process -FilePath $activationPython -ArgumentList @(('"' + $activationScript + '"')) -WorkingDirectory $activationRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $activationRoot 'docs\\ml_evidence\\activation_service.stdout.log') -RedirectStandardError (Join-Path $activationRoot 'docs\\ml_evidence\\activation_service.stderr.log') -PassThru
.\\ai-ml\\.venv\\Scripts\\python.exe docs/ml_evidence/verify_activation_api.py
node docs/ml_evidence/verify_activation_backend.cjs
Get-NetTCPConnection -State Listen -LocalPort 8000 | Select-Object LocalAddress,LocalPort,OwningProcess
Set-Location backend
npm test -- --silent
Set-Location ../ai-ml
.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_ml.py tests/test_pipeline.py tests/test_benchmark.py -k "not train_and_predict_small and not invalid_datasets and not order_and_leakage and not serialization_frozen_evaluation_and_backup and not loaded_prediction_contract and not llm_provider_failure_and_benchmark_separation and not modified_split_is_rejected"
Set-Location ..
.\\ai-ml\\.venv\\Scripts\\python.exe docs/ml_evidence/write_activation_report.py
```

## Files changed by this activation task

Existing files changed:

- `ai-ml/.env`: only the two model/metadata paths.
- `docs/ml.md`: current activation status and report links.

New reports:

- `docs/ML_ACTIVATION_REPORT.md` (this report).
- `docs/ML_ACTIVATION_FOLLOWUPS.md`: zero-value preprocessing, LLM dietary enforcement, explanation wording and provenance limitations; all remain open.

New verification scripts under `docs/ml_evidence/`:

- `activation_control.py`, `serve_verified_model.py`, `verify_activation_api.py`, `verify_activation_backend.cjs`, `write_activation_report.py`.

New evidence under `docs/ml_evidence/`:

- `activation_preflight.json`, `activation_config.json`, `activation_runtime.json`, `activation_api.json`, `activation_backend_initial.json`, `activation_backend.json`, `activation_listener.json`, `activation_integrity.json`, `activation_service.stdout.log`, `activation_service.stderr.log`.

The historical verification report/evidence are preserved. No dependency changes, retraining, production-data changes, commits or pushes occurred. The service is local; no external deployment was performed.
'''
(ROOT/'docs/ML_ACTIVATION_REPORT.md').write_text(report,encoding='utf8')
print(json.dumps({'report':'docs/ML_ACTIVATION_REPORT.md','verified_pid':identity['pid'],'integrity':integrity},indent=2))
