# Verified baseline audit — 2026-10-16

Discovery was completed before application changes. Existing uncommitted work is recorded in
`ml_evidence/preexisting_changes.patch`; original dataset/artifact hashes are in
`ml_evidence/original_files.json`. No AGENTS.md was found in the repository.

## Architecture and inspected sources

React/Vite calls Express, which owns authentication, MongoDB, profile calculations,
rule filtering and ranking. Express calls Python FastAPI for a six-class focus prediction.
Inspected root README, docs/{architecture,api,ml}.md, dependency manifests, Python config,
main.py, training/{train,dataset,evaluate,retrain}.py, preprocessing/pipeline.py,
features/engineering.py, prediction/predictor.py, evaluation/metrics.py, all existing
Python tests, backend mlService/featureBuilder/mlController/mlRoutes, validation,
medicalRules, AI service, and frontend MLExplanation. Inspected all eight package files,
both data-directory CSVs, and model metadata. Model binaries exist at models/model.pkl
and models/random_forest_model.joblib (9,874,521 bytes each); prediction loads lazily,
with an existing fallback to the latter filename. Startup does not train.

## Original workflow

`train()` generates 3,000 profiles with seed 42 and never reads a CSV. The 200-row
sample_training_data.csv is illustrative, not the original trainer's input. The classifier
uses 200 trees, depth 12, minimum leaf 3, balanced class weights and seed 42. An 80/20
stratified split gives 2,400 training and 600 test examples; no validation set exists.
Raw values use fixed imputation, code mappings and ratios, with no learned preprocessing.
`save()` previously overwrote model.pkl and feature_metadata.json without backup.
`/evaluate` previously trained a new model rather than evaluating the loaded artifact.
Feedback retraining compared test accuracy across changing datasets, allowing test-based
promotion and self-reinforcement from earlier model labels.

Features: bmi, age, activity_score, sleep_hours, sleep_adequacy, hydration_ratio,
hydration_adequacy, exercise_minutes, exercise_adequacy, steps_ratio, calorie_ratio,
stress_level, goal_code, gender_code. Labels: activity_focus, balanced_wellness,
fitness_improvement, hydration_focus, sleep_focus, weight_management.

Original trainer was executed without saving: accuracy **0.9017**, weighted precision
**0.9000**, weighted recall **0.9017**, weighted F1 **0.8984**, macro F1 **0.846610**.
Full per-class results, confusion matrix and measured time: `ml_evidence/original_baseline.json`.
This is a historical reference, not a paired comparison with the new split.

## Environment and checks

Python 3.13.5; numpy 2.1.3; pandas 2.2.3; scikit-learn 1.6.0; joblib 1.4.2;
FastAPI 0.115.6; Pydantic 2.13.5; pytest 8.3.4; httpx 0.28.1.
Declared Python pins match the installed direct dependencies checked.
Backend declares Express ^4.21.2, Mongoose ^8.9.3; frontend React ^18.3.1, Vite ^5.4.11.
Exact installed JS dependencies will be recorded with final verification.
Original ML suite: 9 passed, exit 0; backend: 43 passed, five suites, exit 0.
Windows sandbox initially prevented Jest cache writes and hung FastAPI TestClient;
approved unsandboxed reruns passed. Backend tests unexpectedly call the configured Gemini
provider and report that gemini-1.5-flash is unavailable. No credential value was printed.

## Dataset compatibility

The package has the stated eight files. Raw/features: 20,000 x 15; benchmark: 200 x 15;
sample: 200 x 15. No missing cells or duplicate rows. The copied feature file has the
same SHA-256 as the package. Every engineered value matches existing preprocessing.
The raw rows and labels reproduce generator seed 42 exactly. Benchmark labels reproduce
seed 2026. There is no exact training/benchmark feature overlap. Rules plus nominal 7%
random relabelling produce 1,155 actual label changes (5.775%, since a random choice can
retain the original label). Class counts: 850 activity, 2,183 balanced, 1,755 fitness,
3,326 hydration, 5,200 sleep, 6,686 weight. Package claims about a 20,000-row default and
export_dataset.py do not match this checkout. Package 1.8.0 metrics are external claims.

## Risks and implementation decisions

- Synthetic rule agreement cannot establish real-world wellness benefit or medical validity.
- Preserve data and old artifacts; write a separate versioned model under existing models/.
- Add strict CSV/input validation, provenance hashes and reproducible 60/20/20 splits.
- Select among dummy, scaled logistic regression, original Random Forest and gradient
  boosting on validation macro F1 only; evaluate the selected model once on the test set.
- Keep benchmark profiles out of selection. Check exact and defined near-duplicate overlap.
- Retain the API envelopes; protect expensive endpoints with a disabled-by-default admin
  token, and restrict backend feedback retraining to explicitly configured administrators.
- Prevent automatic promotion based on test metrics. Remove unsupported clinical guarantees
  from the explanation UI. Document remaining medical/privacy review needs.
- Implement strict structured LLM evaluation with real errors, no fabricated scores, and
  pending human ratings. The configured provider's unavailable model may block that arm.
