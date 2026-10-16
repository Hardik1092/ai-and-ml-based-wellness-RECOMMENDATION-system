# ML runtime verification report

Verified 2026-10-16 using synthetic profiles only. No clinical validity is claimed.

**Overall: FAIL for the claim that the latest training artifact is the configured runtime artifact; NOT VERIFIED for a running deployment.** The latest saved winner is **HistGradientBoostingClassifier**, not a newly trained Random Forest. The configured loader still selects the original **RandomForestClassifier**. This is consistent with the earlier instruction not to activate the candidate.

No service listened on ports 8000, 5000 or 5173. Unsandboxed localhost requests to ML health/metadata, backend health and frontend all failed with `ConnectError: [WinError 10061] ... target machine actively refused it`. Process inspection found no Python service. No service was started or restarted. Therefore there is no verified live-process model path/hash, live authenticated recommendation request, or browser rendering result. The runtime path below is the resolved configuration and the artifact actually loaded by the existing loader in an isolated audit process, not proof about a running deployment.

## Artifact identity

| Role | Resolved absolute path | SHA-256 | Loaded Python type |
| --- | --- | --- | --- |
| configured_runtime | C:\Users\ASUS\Desktop\cep my\CEP_Project\ai-ml\models\model.pkl | 9c5d7598ba2b33ad1155d1780b6021dd923f8fcc34bfe250236246ce3453c29c | RandomForestClassifier |
| latest_training | C:\Users\ASUS\Desktop\cep my\CEP_Project\ai-ml\models\cep-20k-v1\model.pkl | 4d131cc7cbd2b8350cc1338adf8cc2f6447a6f3b889feb18b8e4fe7b0ef7729e | HistGradientBoostingClassifier |

The two paths and hashes differ. The legacy fallback `ai-ml/models/random_forest_model.joblib` has the same SHA-256 as `models/model.pkl`. Both models' actual `feature_names_in_` and class arrays match the application's feature/class contract. `cep-20k-v1/feature_metadata.json` declares the candidate checksum and scikit-learn 1.6.0; the original metadata lacks a model checksum.

Training is in `ai-ml/app/training/train.py`: the historical `train()` produces the original Random Forest; the latest `run_experiment()` fits four candidates on training rows and selects validation macro F1. The selected already-fitted HGB is written to the explicitly supplied new output directory. `experiment.json` and `feature_metadata.json` identify `hist_gradient_boosting`; test evaluation does not refit it. Training does not activate a runtime path.

`ai-ml/app/config.py` resolves relative paths against `ai-ml/`. Current `.env` selects `models/model.pkl` and `models/feature_metadata.json`; existing process environment variables would override dotenv. The audit process resolved exactly the paths above. A future service launched with different environment values could differ.

`load_model()` in `app/prediction/predictor.py` tries the configured path, then `random_forest_model.joblib` in that directory if the file is missing. It verifies metadata checksum/version when present, feature order and classes, then caches the loaded object in process-global `_state`. Disk changes alone do not reload an already cached model. Legacy metadata without provenance weakens identity checking. The metadata/prediction `model_type` field is metadata-derived (with an RF fallback label), not independent attestation of the Python type; this audit inspects the actual object instead.

## Input contract and preprocessing

Exact ordered features:

`bmi`, `age`, `activity_score`, `sleep_hours`, `sleep_adequacy`, `hydration_ratio`, `hydration_adequacy`, `exercise_minutes`, `exercise_adequacy`, `steps_ratio`, `calorie_ratio`, `stress_level`, `goal_code`, `gender_code`.

The original RF and selected HGB consume these engineered values without scaling. The logistic candidate alone used training-fitted StandardScaler. BMI is computed from height and weight; backend health metrics derive water/calorie targets. Seven-day logs are summarized, with profile/default substitutions. Sleep defaults to 7 h, exercise/steps to 0, stress to 3, and missing water/calories to personal targets (otherwise 2500 ml/2000 kcal). Sleep adequacy is >=7 h, exercise adequacy >=30 min, hydration adequacy >=0.9. Steps divide by 8000; hydration and calorie ratios divide by personal targets. Continuous features are rounded at the documented precision. Python-compatible rounding is implemented in the backend.

Activity codes: sedentary=1, light=2, moderate=3, active=4. Goal codes: weight_loss=0, weight_gain=1, muscle_building=2, maintain_weight=3, improve_fitness=4, improve_sleep=5, general_wellness=6. Gender codes: male=0, female=1, other=2. Finite values, numeric bounds, integer codes, adequacy consistency and combined sleep/exercise daily time bounds are validated. These are computational constraints, not clinical eligibility rules.

**FAIL — zero-value handling:** `buildMlFeatures()` uses `avg_sleep || profile.sleep_hours` and `avg_water || profile.water_intake_ml`; zero logs are silently replaced. On this synthetic profile, zero sleep becomes 8 h and zero water becomes ratio 0.949. Zero calories become ratio 1 through `raw.calories || calorieTarget` in both feature builders. This differs from treating valid zero as observed data. No fix was applied.

## Prediction endpoint and trace

`POST http://127.0.0.1:8000/predict` is the actual ML endpoint. FastAPI's generated schema is saved in [runtime_openapi.json](ml_evidence/runtime_openapi.json). `PredictRequest` accepts `features: dict = {}` and optional `raw: dict`; raw takes precedence. Engineered input needs all 14 fields; raw needs numeric age/BMI, accepts named goal/gender/activity values and optional log/target fields. Example actual feature payload:

```json
{
  "features": {
    "bmi": 22.86,
    "age": 30,
    "activity_score": 3,
    "sleep_hours": 8,
    "sleep_adequacy": 1,
    "hydration_ratio": 1,
    "hydration_adequacy": 1,
    "exercise_minutes": 30,
    "exercise_adequacy": 1,
    "steps_ratio": 1,
    "calorie_ratio": 1,
    "stress_level": 3,
    "goal_code": 6,
    "gender_code": 0
  }
}
```

Flow inspected:

1. Backend `buildContext()` converts the profile, computes metrics and summarizes logs; `buildMlFeatures()` builds the ordered inputs.
2. `mlService.predictCategory()` sends `{features}` to `/predict`, with a 4000 ms timeout. No prediction override is set in normal module initialization. Its exported test override is used by automated tests.
3. FastAPI validates, then invokes the loaded object's real `predict()` and `predict_proba()`. Probabilities are rounded to four decimals. No constant predicted category or response cache is used. Static labels, descriptions and global feature importances are explanations, not substituted inference.
4. On unavailable/disabled/failed ML, backend sets the category to null and uses rules-only recommendations. The real backend client returned `available:false`, `Prediction failed; using rule-based output.` against the stopped service.
5. Nutrition filters foods before scoring; category-dependent bonuses up to 0.15 affect ranking and selection within meal budgets. Activity eligibility applies difficulty caps before category bonuses, ranking and distinct-category selection. Nutrition targets and activity limits are rule-derived; ML does not replace them. Confidence is displayed but does not scale ranking bonuses.
6. Controllers generate then upsert recommendation records. These authenticated GET requests have database side effects, so they were not exercised on production data. No stale recommendation lookup was found in these generation paths; the in-process model itself is cached until explicit reload/restart.
7. `Nutrition.jsx` renders `plan.meals[*].items`, each item reason and `data.why`; `Activity.jsx` renders selected activities and reasons. `MLExplanation.jsx` displays the prediction/probabilities and labels global importance as global. This rendering path was inspected in source, not observed in a live browser.
8. The optional LLM branch adds separate narrative recommendations and may replace `why` with its summary. That call receives profile/metrics/log summary, not the ML prediction; its narrative cannot be claimed to be driven by the ML category. Catalog plans remain separately included.

## Actual isolated prediction tests

The audit calls the existing FastAPI app with TestClient, using the unchanged configured loader. It also loads the candidate directly for comparison without changing loader configuration. Backend-generated engineered inputs equal Python raw preprocessing for all 11 profiles; raw and engineered endpoint responses match, and all API probability vectors match direct inference from the configured RF exactly after rounding. All 22 valid endpoint calls returned HTTP 200 and `available:true`.

Baseline: age 30, male, 175 cm, 70 kg, moderate activity, general_wellness goal, vegetarian, peanut allergy, sleep 8 h, exercise 30 min, 8000 steps, water/calories equal personal targets, stress 3. Each row changes one source field from baseline; `low_movement` changes steps only from `exercise_0min`. Goal/weight/age changes naturally recompute dependent metrics, so they are single raw-input interventions, not single engineered-column interventions.

| Case | Comparison parent | RF class | RF max probability | Candidate class | Candidate max probability |
| --- | --- | --- | --- | --- | --- |
| baseline | baseline | balanced_wellness | 0.7885 | balanced_wellness | 0.9791 |
| sleep_5h | baseline | sleep_focus | 0.914 | sleep_focus | 0.97 |
| sleep_7h | baseline | balanced_wellness | 0.8082 | balanced_wellness | 0.9718 |
| water_800ml | baseline | hydration_focus | 0.9086 | hydration_focus | 0.9676 |
| exercise_0min | baseline | balanced_wellness | 0.4803 | balanced_wellness | 0.9613 |
| steps_1000 | baseline | balanced_wellness | 0.7364 | balanced_wellness | 0.9807 |
| goal_fitness | baseline | fitness_improvement | 0.5067 | fitness_improvement | 0.9145 |
| weight_95kg | baseline | weight_management | 0.8939 | weight_management | 0.9749 |
| age_55 | baseline | balanced_wellness | 0.7707 | balanced_wellness | 0.9759 |
| stress_5 | baseline | balanced_wellness | 0.7837 | balanced_wellness | 0.969 |
| low_movement | exercise_0min | activity_focus | 0.7634 | activity_focus | 0.9916 |

Full per-class probability vectors, inputs, candidate outputs, timings and parity checks are retained in [runtime_audit.json](ml_evidence/runtime_audit.json). Same class across some interventions is expected: sleep 8→7 h changes RF maximum probability from 0.7885 to 0.8082 while remaining balanced. Exercise alone dropping to zero leaves 8000 steps and remains balanced with probability 0.4803; lowering steps next produces activity_focus. Both artifacts agree on these 11 classes but have different probability vectors; this does not establish equivalence.

Repeated baseline requests were identical. Missing fields returned HTTP 200/available:false; a list instead of a feature object returned 422; raw sleep=25 returned HTTP 200/available:false. No valid prediction errors occurred. A joblib physical-core discovery warning fell back to logical cores; it did not prevent inference.

## Evidence of recommendation influence

An isolated Node process used the real `generateNutritionPlan()` and `recommendToday()` functions with 58 seed Food and 28 seed Activity documents held in memory. Only catalog read methods were substituted in that short-lived process; model outputs were the actual saved-artifact predictions above. No database was connected or seeded. For each identical profile/metrics/catalog, a null-category control was compared with its actual predicted category. This isolates the category's causal effect on ranking; it is component integration evidence, not a live HTTP/browser end-to-end test.

| Case | Applied class | Meal selection/order changed vs null category | Activity selection/order changed vs null category |
| --- | --- | --- | --- |
| baseline | balanced_wellness | False | False |
| sleep_5h | sleep_focus | True | False |
| sleep_7h | balanced_wellness | False | False |
| water_800ml | hydration_focus | True | False |
| exercise_0min | balanced_wellness | False | False |
| steps_1000 | balanced_wellness | False | False |
| goal_fitness | fitness_improvement | True | False |
| weight_95kg | weight_management | True | False |
| age_55 | balanced_wellness | False | False |
| stress_5 | balanced_wellness | False | False |
| low_movement | activity_focus | True | True |

For sleep_focus, breakfast replaces Idli with Sambar with Masala Oats and dinner replaces Vegetable Khichdi with Palak Dal. For hydration_focus, breakfast becomes Sprouts Salad and Soy Milk Smoothie. For low_movement/activity_focus, the activity control is **Evening Stroll, Sun Salutations, Full Body Stretch**; the model-assisted result is **Evening Stroll, Hip and Shoulder Mobility, Sun Salutations**. The changed activity ranking includes a 0.15 category bonus. This demonstrates both food and activity selection influence without assuming every profile change must alter a class or every bonus must alter selection.

The balanced category adds the same 0.06 bonus to all foods, so their ordering can remain unchanged despite item explanations saying they were ranked higher. This is an explanation accuracy issue: a higher numeric score is not necessarily a higher relative rank. Evidence with all scores, bonuses, selected items and reasons: [runtime_recommendations.json](ml_evidence/runtime_recommendations.json).

## Regression and safety

**PASS, bounded to catalog behavior:** 168 combinations (3 dietary preferences × 8 allergen settings × 6 categories plus null) produced zero selected-food violations in the seed catalog. Vegetarian/vegan flags and recorded allergen tags were checked, in addition to the application's own eligibility predicate. All seven sedentary category/control runs selected only easy activities. These checks establish independence from the prediction for the tested catalog, not universal ingredient/synonym coverage.

**FAIL, broader UI guarantee:** the separate LLM narrative is not validated by the catalog predicate. `validateLlmOutput(parsed, allergies)` checks literal allergen text and unsafe phrases, but receives no dietary preference. Vegan/vegetarian compliance is only prompted there; synonym/ingredient inference is not guaranteed. Source inspection establishes this missing enforcement; no unsafe live LLM recommendation was generated in this audit. A model classification benchmark without allergy fields does not validate these UI safeguards.

**PASS:** backend regression, 6 suites / 51 tests; isolated MongoMemoryServer, provider credentials disabled in test process, fixture ML prediction. These tests do not prove live model identity. **PASS:** 28 Python tests, 13 deliberately deselected to avoid fitting/retraining any model. Selected tests cover inference, input rejection, saved artifact loading, feature parity, benchmark parsing/retries and preflight. Warnings: Starlette/AnyIO deprecation and joblib physical-core discovery fallback. Jest force-exited under the repository's existing test command. No dependencies were changed.

## Findings

| Status | Finding |
| --- | --- |
| FAIL | Latest artifact differs from configured loader path/hash/type; latest winner is HGB, original is RF. |
| NOT VERIFIED | Exact artifact loaded by a currently running ML service: no reachable service existed. |
| PASS | Actual isolated loader type/features and all tested direct/API probability vectors agree. |
| PASS | Controlled real predictions change food and activity selections in isolated component tests. |
| NOT VERIFIED | Live authenticated backend-to-ML-to-browser flow and user-visible rendering. |
| PASS | Catalog diet/allergy filtering and sedentary difficulty caps hold independently of category in tested cases. |
| FAIL | Zero log values are overwritten by defaults/profile data. |
| FAIL | Separate LLM narrative lacks deterministic dietary-preference enforcement. |
| FAIL | Some explanation wording claims rank changes when only a uniform score bonus occurred. |
| PASS | 51 backend and 28 no-training Python regressions passed. |
| PASS | All 13 preserved original files, four configuration files, and candidate model/metadata hashes unchanged. |

## Minimal recommendations — not implemented

1. Decide explicitly whether the original RF or saved HGB should be active. If the candidate is approved later, configure both model and metadata paths together, restart deliberately, then verify a reported loaded-artifact checksum. Do not rename HGB as Random Forest or infer promotion from a successful training run.
2. Add read-only runtime provenance from the loaded object: resolved artifact path, loaded SHA-256, model type, feature order and load time. Require matching metadata/checksum for legacy/fallback artifacts, and avoid silent stale fallback where identity matters.
3. Preserve valid zero logs with null/missing checks; add focused regression cases for zero sleep, water and calories.
4. Enforce allergies/dietary restrictions on all generated narrative food suggestions using structured validated food identities/ingredients; prompt instructions alone are insufficient. Keep rule-derived limits independent of predictions.
5. Say the category contributed a score bonus unless a relative-rank change is measured; label probabilities as model probabilities rather than clinical confidence.
6. After findings are reviewed and a deliberate service start is authorized, repeat the live identity checks and end-to-end UI flow with a disposable synthetic account/database.

No recommended fix, retraining, activation, deployment, dependency change, production data write, commit or push was performed during this investigation. Evidence/report files are the only new changes for this runtime task; the repository already contained earlier work.

## Exact commands and evidence

From repository root in PowerShell:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,5000,5173 } | Select-Object LocalAddress,LocalPort,OwningProcess
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node' } | Select-Object ProcessId,Name,ExecutablePath
.\ai-ml\.venv\Scripts\python.exe docs/ml_evidence/runtime_audit.py
node docs/ml_evidence/runtime_recommendations.cjs
Set-Location backend
npm test -- --silent
Set-Location ../ai-ml
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py tests/test_ml.py tests/test_pipeline.py tests/test_benchmark.py -k "not train_and_predict_small and not invalid_datasets and not order_and_leakage and not serialization_frozen_evaluation_and_backup and not loaded_prediction_contract and not llm_provider_failure_and_benchmark_separation and not modified_split_is_rejected"
Set-Location ..
.\ai-ml\.venv\Scripts\python.exe docs/ml_evidence/write_runtime_report.py
```

The initial sandbox process inspection was unavailable; the read-only inspection and localhost probes were repeated with approved unsandboxed access and confirmed connection refusal. Audit scripts use existing artifacts; they do not run training. `runtime_profiles.cjs` is invoked by the Python audit and uses the application feature builder. Artifact SHA-256 values use Python hashlib over file bytes. [final_integrity.json](ml_evidence/final_integrity.json) records unchanged-file checks. Re-running scripts refreshes audit evidence, not application state.

The independently completed 200-case benchmark, including exact execution commands, genuine Gemini responses, failure counts, latency, cost estimate and separate subjective review, is in [CEP_ML_LLM_COMPARISON_REPORT.md](CEP_ML_LLM_COMPARISON_REPORT.md). It evaluates the saved candidate directly and does not imply deployment.
