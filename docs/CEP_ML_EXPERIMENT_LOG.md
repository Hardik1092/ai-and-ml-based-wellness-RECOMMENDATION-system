# Experiment log and remaining limits — 2026-10-16

## Phase status

| Stage | Status | Evidence |
|---|---|---|
| A — inspect | Completed | Baseline audit; original hashes and preexisting diff |
| B — report | Completed | Verified findings and plan presented before application edits |
| C — implement | Completed | Existing trainer extended; validation, authorization, artifact provenance and UI wording |
| D — train | Completed | Original 3,000-row baseline plus four candidates on the 20,000-row CSV |
| E — evaluate | Completed | Frozen 4,000-row test; serialization/reload reproduces metrics |
| F — benchmark | Partly completed / Blocked | 200 ML/rule outputs; Gemini HTTP 404, zero generated outputs |
| G — verify | Completed after correction | Final test/build counts below; feature parity fixed |
| H — document | Completed | Five reports, setup, raw evidence and exact commands |
| Clinical/human evaluation | Not Started | Requires representative data and qualified reviewers |
| Commit / push / deploy / activate model | Not Started | Not performed; candidate is separate from original active configuration |

## Material changes and reasons

- ai-ml/app/preprocessing/validation.py: shared finite/numeric/bounds/schema checks;
  reject missing paths, invalid targets, duplicates and cross-set leakage.
- ai-ml/app/training/train.py: retain historical generator baseline; add explicit CSV
  experiment, stratified 60/20/20 split, validation-only selection, four candidates,
  environment/provenance/latency/size records, split membership and backups on save.
- ai-ml/app/training/validate_dataset.py: reproduce package schemas, generator labels,
  class distributions, raw-feature agreement and exact/defined-near overlap.
- ai-ml/app/training/evaluate.py: evaluate saved model on checksum-verified test split.
- ai-ml/app/training/retrain.py: prevent feedback-based promotion using model-derived
  labels and incomparable test scores. Independently reviewed labels are needed first.
- ai-ml/app/evaluation/{metrics,benchmark}.py: macro/weighted/per-class/confusion metrics,
  probability losses, common-task ML/rule/LLM evaluation, strict JSON output and explicit
  provider/failure/pending records. Cost stays null without measured billing/rates.
- ai-ml/app/main.py: preserve prediction envelopes; protect expensive endpoints with
  disabled-by-default administrator token; validate raw and engineered inputs.
- ai-ml/app/prediction/predictor.py: preserve the preexisting filename fallback; verify
  artifact feature/class/version/checksum contract and describe probabilities honestly.
- backend env, mlAdmin middleware, mlRoutes and mlService: authenticated administrator
  restriction plus service-token propagation. Updated both .env.example files; actual
  secret files were not edited or printed.
- backend featureBuilder: replace Math.round with exact Python-compatible rounding.
  A new cross-language test exposed the discrepancy; all 20,000 rows now agree.
- backend numeric validator: reject booleans, objects and non-finite values.
- backend AI service: conservative urgent-symptom message before any provider request.
  Existing uncommitted AI-service changes remain. This keyword guard is not triage.
- frontend MLExplanation and backend explanation text: remove clinical guarantees,
  weighted/macro confusion, false normalized-feature wording and false fallback state.
  A model without built-in feature importance no longer implies service failure.
- Python/backend tests: new coverage described below. Backend test setup now disables
  external providers so tests cannot spend credentials or transmit profiles.
- scripts/report-ml.py: render reports from actual saved evidence, without retraining.

The saved initial diff separates preexisting user changes from this work. Original
13 data/package/artifact files were hash-checked unchanged. No production resources,
Git commits or remote branches were modified. No dependencies were installed.

## Executed commands and outcomes

Commands from repository root unless specified. Windows sandbox retries were approved.

| Command / operation | Exit | Outcome |
|---|---|---|
| Original train(3000), no save | 0 | Accuracy .9017, macro F1 .846610, weighted F1 .898442 |
| Initial npm test inside sandbox | 1 | Jest transform-cache EPERM; 0 tests ran |
| Initial npm run test:ml inside sandbox | No completion | Stalled in TestClient; superseded by approved rerun |
| Baseline npm run test:ml outside sandbox | 0 | 9 passed |
| Baseline npm test outside sandbox | 0 | 43 passed; exposed unwanted provider calls and unavailable Gemini model |
| python -m app.training.validate_dataset with paths in docs/ml.md | 0 | All checks completed; zero exact/near split or benchmark overlap |
| python -m app.training.train --dataset data/cep_ml_features_20000.csv --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir models/cep-20k-v1 --seed 42 (ai-ml/) | 0 | Four candidates; HGB selected before test evaluation |
| python -m app.training.evaluate --run-dir models/cep-20k-v1 (ai-ml/) | 0 | Same frozen test metrics |
| Benchmark --output-dir ../docs/ml_evidence/benchmark-v1 --llm (ai-ml/, other paths in docs/ml.md) | 0 | ML/rules complete; sandbox network failure recorded |
| Benchmark --output-dir ../docs/ml_evidence/benchmark-provider-v1 --llm, approved network rerun | 0 | ML/rules complete; Gemini HTTP 404 recorded, 199 cases pending |
| Expanded ML suite before parity test | 0 | 30 passed |
| Expanded ML suite with parity test | 1 | 32 passed, 1 failed: Python/JavaScript rounding disagreement |
| Full 20,000-row cross-language parity check after correction | 0 | Zero mismatching cells at 1e-9 tolerance |
| npm test after reliability changes | 0 | 51 passed, 6 suites |
| npm run build | 0 | Vite production build successful |

Final rerun results after the rounding correction are appended below. Benchmark CLI
exit 0 means the report was successfully written, not that the provider succeeded;
summary.json carries per-system status. The configured model was not changed to hide
its HTTP error. Plot dependency probes found no matplotlib; no dependency was installed.

## Safety checks implemented and limits

Application bounds are computational input contracts, NOT recommended values:
raw age 10–100, BMI 4–400, weight 25–300 kg, sleep 0–24 h, water 0–10000 ml,
water target 500–15000 ml, exercise 0–1440 min, steps 0–100000, calories 0–20000,
calorie target 500–10000, stress integer 1–5. Engineered activity codes 1–4,
indicators 0/1, goal codes 0–6, gender codes 0–2, steps ratio 0–12.5 and water/calorie
ratios 0–20. Integer codes and indicator consistency are checked. Hydration indicator
allows a .0005 rounding tolerance because it was calculated before ratio rounding.
Age/BMI are required; existing optional missing-log imputation remains explicit.
No clinical thresholds were invented to claim medical suitability.

The urgent-symptom guard responds before external AI to common English phrases for
chest symptoms, severe breathing difficulty, unconsciousness, severe bleeding and
coughing blood. Its general escalation wording is informed by
[NHS emergency guidance](https://www.nhs.uk/symptoms/shortness-of-breath/) and
[London Ambulance examples](https://www.londonambulance.nhs.uk/our-services/emergency-care/calling-999/).
It gives no diagnosis, drug advice or location-specific emergency number. It can
miss wording/languages and over-trigger on negated/hypothetical statements. It is
not a validated emergency detection system, and other product entry points do not
implement comprehensive symptom triage.

Remaining material risks requiring product/qualified review:

- Existing health-metric formulas accept broad profile ranges, including children
  and extreme body measurements. Adult-style BMI bands and targets are not validated
  for these groups. Water/calorie/protein formulas and chronic-condition messages
  require qualified review; a numeric range check cannot make their advice safe.
- medicalRules.js includes claims such as a renal protein cap that are not proven by
  the rule message alone. Do not present the current product as medically safe.
- The existing live LLM recommendation path can provide narrative recommendations,
  not merely reword rule outputs. README/architecture's earlier 'wording only' claim
  was incomplete. Keyword/allergen checks cannot prove safety or complete constraint
  enforcement; the classification benchmark does not validate that narrative path.
- No consented real-world dataset, clinical benefit study, independent human labels,
  qualitative ratings, subgroup validation or repeated LLM measurements exist.
- General-purpose assistant outputs still need broader post-generation safety review.
  Prompt instructions alone do not guarantee absence of unsupported medical claims.
- Profile/medical context is sent to configured external AI in normal application use.
  Tests now disable providers. Production privacy consent, retention, access auditing,
  vendor data policies and redaction of arbitrary provider/error text need review.
  Current error handlers may log messages/stacks; do not claim privacy certification.
- ML metadata exposes local provenance paths on the internal service. Keep it internal.
  Signed artifact distribution, concurrency/resource controls for multiple authorized
  training jobs and encrypted remote transport remain deployment concerns.

## Interpretation

This work establishes a reproducible engineering demonstration and recorded synthetic
rule agreement. It does not establish real-world wellness effectiveness, clinical safety,
LLM inferiority or an independently validated diagnosis. The comparison's LLM arm is
blocked on an available configured model; human evaluation requires reviewers.

## Final verification

After the rounding fix and combined daily-time validation:

- `npm run test:ml`: **34 passed**, exit 0, 8.42 seconds; three documented dependency warnings.
- `npm test`: **51 passed**, six suites, exit 0, 8.646 seconds.
- `npm run build`: exit 0, 1,950 modules transformed; no subsequent frontend code changes.
- `python -m compileall -q ai-ml/app scripts/report-ml.py`: exit 0.
- Scoped `git diff --check` on this task's modified tracked paths: exit 0.
- Whole-repository diff check still flags a preexisting trailing blank line in
  backend/src/middleware/rateLimiter.js; that user's change was left intact.
- The initial sandbox TestClient process was interrupted after the successful
  unsandboxed runs (exit 1, no test result). It was not counted as a passing run.
- Original artifact inference latency was measured separately using 100 seed-900
  generated profiles after one warmup and saved in original_baseline.json.
- Safety audit completed with partial safeguards; the unresolved clinical/product
  risks above remain explicitly open. Sleep plus exercise exceeding 24 hours is
  now rejected in both raw and engineered input validation.
