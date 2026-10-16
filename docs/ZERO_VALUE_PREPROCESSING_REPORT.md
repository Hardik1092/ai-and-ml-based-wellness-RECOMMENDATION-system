# Zero-value preprocessing fix

Status: **PASS for source implementation and regression tests.** No claim of a
restarted or redeployed service is made. The separate LLM dietary-enforcement gap
remains open.

## Scope and caller semantics

Inspected the working tree and activation, follow-up and runtime reports before
editing. The backend feature builder already contained Python-compatible rounding
work; it was preserved. Recorded 268 existing file hashes and exact pre-edit source
copies in `docs/ml_evidence/zero-value-fix/` for verification and scoped rollback.

Log validation accepts numeric zero for sleep, water and calories. Optional empty,
null or absent API values are normalized to null by validation. Daily log persistence
preserves zeros, and aggregation excludes only null/undefined observations, retaining
zeros in averages. `buildContext()` passes these aggregates to `buildMlFeatures()`.
Existing daily-log upsert behavior skips null updates; this was not changed.

Both production raw-feature callers impute missing observations before construction.
Python `/predict` also validates raw values first. No broad truthiness replacement
was made: zero targets are not legitimate divisors, and stress zero is outside its
1–5 contract. Target fallbacks, encoding, rounding, ordering, validation, and other
preprocessing remain unchanged.

## Exact implementation

- `backend/src/services/featureBuilder.js`: change logged sleep/profile and logged
  water/profile fallback from `||` to `??`; change calorie intake/target fallback
  from `||` to `??`.
- `ai-ml/app/features/engineering.py`: replace calorie truthiness fallback with an
  explicit `None` check. Python already preserves zero sleep and water through its
  validated/imputed pipeline, so these needed no Python change.

Result: zero sleep stays 0 with adequacy 0; zero water stays ratio 0 with adequacy 0;
zero calories stays ratio 0. Missing logs still use profile sleep/water where present,
then the existing defaults. Missing calories still default to the personal target.
Missing observations with no profile/targets still use sleep 7 h, water 2500 ml and
calories 2000 kcal. Legitimate profile sleep/water zeros also survive missing logs.

## Tests and actual commands

Focused tests cover separate zeros, null/undefined/absent defaults, zero log precedence,
zero profile values, mixed missing/zero aggregation, and persisted zero logs reaching
the recommendation inference request. The backend integration test captures features
at the ML boundary; it does not fabricate a successful real-model prediction.
Python additionally checks the raw FastAPI preprocessing boundary and exact backend/
Python parity across all 64 combinations of absent, null, zero and positive values
for sleep, water and calories.

From `ai-ml/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_zero_value_features.py
```

**9 passed**, 1.55 s. The initial pre-fix sandbox attempt visibly reproduced a failure
at the zero-calorie test, then stalled on the Node subprocess. It was stopped; it is
not counted as a completed test run. The completed focused and broader runs used
approved unsandboxed execution.

From `backend/`:

```powershell
npm test -- --runTestsByPath tests/zeroValueFeatures.test.js
npm test -- --silent
```

Focused: **8 passed**, 1 suite, 3.498 s. Full backend: **59 passed**, 7 suites, 9.402 s.
Tests use disposable MongoDB and external AI is disabled by the existing setup;
no production data is modified.

From `ai-ml/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -k "not train_and_predict_small and not order_and_leakage and not serialization_frozen_evaluation_and_backup and not loaded_prediction_contract and not llm_provider_failure_and_benchmark_separation and not modified_split_is_rejected"
```

**44 passed, 6 deselected**, 3.47 s. This runs all collected Python tests except six
that fit a model directly or through their experiment fixture. Running the literal
full suite would violate the no-retraining constraint. Invalid-dataset tests remain
included. Existing warnings: Starlette/AnyIO deprecation and joblib's logical-core
fallback. Jest retains the repository's configured force-exit behavior.

Read-only before/after feature comparison used `build_feature_row(impute_raw(row))`
from the saved pre-edit source and current source over both supplied raw CSVs:
**0 changed feature rows / 20,000 training-source rows; 0 / 200 benchmark rows**.
This checks preprocessing compatibility, not new model quality or clinical validity.
Results are in `docs/ml_evidence/zero-value-fix/dataset_compatibility.json`.

## Files changed in this phase

Existing files:

1. `backend/src/services/featureBuilder.js` — three fallback expressions only.
2. `ai-ml/app/features/engineering.py` — explicit missing-calorie handling.
3. `docs/ML_ACTIVATION_FOLLOWUPS.md` — mark the source fix and link this report;
   retain the LLM gap as open.

New files:

4. `backend/tests/zeroValueFeatures.test.js`.
5. `ai-ml/tests/test_zero_value_features.py`.
6. `docs/ZERO_VALUE_PREPROCESSING_REPORT.md`.
7. `docs/ml_evidence/zero-value-fix/before.json` — pre-edit hashes, no secret values.
8. `docs/ml_evidence/zero-value-fix/featureBuilder.js.before` — exact source backup,
   including the user's pre-existing rounding changes.
9. `docs/ml_evidence/zero-value-fix/engineering.py.before` — exact source backup.
10. `docs/ml_evidence/zero-value-fix/dataset_compatibility.json`.
11. `docs/ml_evidence/zero-value-fix/integrity.json` — final preservation check.

## Remaining risks and operational status

The saved model is unchanged. Existing training/benchmark profiles are unaffected,
but previously misrepresented zero observations now correctly produce different
feature vectors and may produce different predictions. Generalization to such
edge profiles is not established by these tests. Zero is an observed value, not a
recommendation to sleep, drink or eat nothing.

No services were restarted. The previously launched non-reloading Python process
may still hold the old feature-construction code; restart long-lived backend/ML
services deliberately before expecting the source correction in live requests.
Fresh test processes verify the new code. The model configuration remains on
`cep-20k-v1`; no model rollback or activation changes were made.

LLM dietary enforcement, explanation wording, and null-log clearing semantics are
unchanged. No dependencies, credentials, production data or model artifacts changed;
no training, commit or push occurred.

## Scoped rollback

Do not use `git checkout` or a blanket reset: the backend file contains earlier work.
To revert this fix only, change the three `??` expressions listed above back to `||`,
and restore the Python expression:

```python
calorie_ratio = (raw.get("calories") or calorie_target) / calorie_target
```

If no later source edits have been made, these exact pre-edit copies provide a
convenient rollback preserving all earlier work, from repository root:

```powershell
Copy-Item -LiteralPath docs/ml_evidence/zero-value-fix/featureBuilder.js.before -Destination backend/src/services/featureBuilder.js
Copy-Item -LiteralPath docs/ml_evidence/zero-value-fix/engineering.py.before -Destination ai-ml/app/features/engineering.py
```

Review subsequent edits before copying. The new regression tests intentionally fail
on the reverted bug; retain them as pending coverage or revert only these two newly
added test files as part of an explicit rollback. Mark the follow-up open again.
Restart affected long-lived services after either applying or reverting the fix.
Do not run the separate model-activation rollback script for this source-only fix.
