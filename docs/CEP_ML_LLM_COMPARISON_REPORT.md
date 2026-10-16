# Final ML versus LLM comparison — 2026-10-16

Status: **All 200 profiles attempted**.
Saved ML model: `cep-20k-v1` (HistGradientBoostingClassifier). LLM:
`gemini-3.5-flash-lite`, using the existing Gemini `v1beta:generateContent` REST
interface with a benchmark-only CLI override. Application environment/configuration,
original models and the saved ML artifact were not changed. Nothing was activated,
deployed, committed or pushed.

## Diagnosis and model choice

The configured `gemini-1.5-flash` returned HTTP 404/NOT_FOUND: unavailable for
API v1beta or unsupported for generateContent. The same credential successfully
listed models. Therefore this was a model availability problem, not evidence of a
missing key. A listed `gemini-2.5-flash-lite` also returned 404 on a non-benchmark
smoke test, explicitly saying it is no longer available to new users and recommending
`gemini-3.5-flash-lite`. The latter is listed with generateContent support and passed
the same seed-91821 non-benchmark smoke test. No model was chosen by benchmark score.

Exact redacted provider responses and listing:
[gemini-diagnostic-live.json](ml_evidence/gemini-diagnostic-live.json),
[2.5 probe](ml_evidence/gemini-flash-lite-smoke.json),
[3.5 probe](ml_evidence/gemini-35-flash-lite-smoke.json).
The listing version was `3.5-flash-lite-07-2026`; returned model identifiers:
`{"gemini-3.5-flash-lite": 198, "not_returned": 2}`. The response does not provide immutable
weights/version guarantees; future runs may differ under the same model name.

The first full attempt returned a temporary HTTP 503 high-demand error before any
generated benchmark answer. It remains in
[benchmark-gemini35-v2](ml_evidence/benchmark-gemini35-v2/summary.json). The final run
allows at most two retries for transport/HTTP 500/502/503/504 errors, with 2/4-second
backoff. It never retries malformed, unsafe or incorrect generated answers. Every
attempt is retained. Retries cannot be interpreted as best-of-N answer selection.
Permanent errors/429 stop the run; three consecutive exhausted transient cases also stop.

## Methodology and separation

Before any benchmark prediction, checksums for the model, metadata, 20,000-row
dataset, split CSV and benchmark were checked. Split membership and every source
profile hash were reproduced. Train/validation/test counts are 12,000/4,000/4,000.
All 200 raw benchmark rows have labels, no missing cells and no duplicate profiles.
They have **zero exact and defined near-duplicate overlap with each split**.
Near overlap uses the predeclared per-feature tolerances in validate_dataset.py.

The training source and saved candidate metrics confirm selection by validation
macro F1 only. The benchmark was read for leakage checks before training, but was
not fitted, scored or used to tune/select candidates. Recomputing the selection
criterion still chooses hist_gradient_boosting. Evidence: [preflight.json](ml_evidence/benchmark-gemini35-v3/preflight.json).

Model SHA-256: `4d131cc7cbd2b8350cc1338adf8cc2f6447a6f3b889feb18b8e4fe7b0ef7729e`.
Benchmark SHA-256: `43f02e05885381a736c4905322c5a2816c9fcf2c2e7e0ccb1da1dbd8fa41661a`.

All systems receive the same 14 engineered numeric features; reference labels,
case IDs and raw fields unavailable to the ML model are excluded from LLM input.
Feature construction is the existing stateless pipeline. Prompt
`cep-common-category-v1` explicitly provides the ordered synthetic label rules.
ML learned noisy examples of that function. Thus the common task is **synthetic
rule imitation/classification**, not independent wellness reasoning or a comparison
of complete meal/activity plans. The LLM may add short rationale/suggestions, which
have no generated ML narrative counterpart.

Prompt hash: `8fbb9707962a07c40a36af1d62e6234d727d461f23cb6624820fea6e18c22183`. The prompt was not tuned on this run.
Parameters: `{"maxOutputTokens": 1024, "responseMimeType": "application/json"}`. Temperature is omitted because
Google documents sampling parameters as ignored for 3.5 Flash-Lite. Default thinking
settings were used; deterministic generation is not claimed. One-second pacing
between cases is excluded from per-case latency; retry backoff is included.
See [Google migration guidance](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6).
The frozen protocol and access/technical amendments predate generated benchmark
outputs: [BENCHMARK_PROTOCOL_V2.md](ml_evidence/BENCHMARK_PROTOCOL_V2.md).

## Quantitative classification results

Full-set scores retain failed/missing answers as abstentions. Valid-only LLM scores
are also recorded in analysis.json. First-attempt scores do not replace transport
failures with successful retries. All metrics below refer to the same 200 cases.

| System | Reference accuracy | Macro F1 | Weighted F1 | Rule agreement |
| --- | --- | --- | --- | --- |
| ml | 0.9300 | 0.904197 | 0.928662 | 0.9950 |
| rule | 0.9350 | 0.909706 | 0.933625 | 1.0000 |
| llm | 0.8100 | 0.714038 | 0.811596 | 0.8650 |
| llm_first_attempt | 0.5950 | 0.595864 | 0.673659 | 0.6500 |

Reference labels disagree with the deterministic feature-based rules on
**13/200 cases**. Agreement with noisy labels
and execution of the explicit rule task are distinct outcomes. The deterministic
rule baseline is included to make this limitation visible.

Paired ML/LLM errors: `{"ml_correct_llm_wrong": 25, "ml_wrong_llm_correct": 1, "both_correct": 161, "both_wrong": 13, "mcnemar_exact_two_sided_p": 8.046627044677734e-07}`.
The exact McNemar test is a two-sided paired classification comparison; it does not
measure clinical benefit, generalize outside this synthetic sample, or prove
equivalence when non-significant.

Per-class results (precision/recall/F1; macro metrics weight each class equally):

| Class | Support | ML precision | ML recall | ML F1 | LLM precision | LLM recall | LLM F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| activity_focus | 9 | 0.8750 | 0.7778 | 0.8235 | 0.5455 | 0.6667 | 0.6000 |
| balanced_wellness | 20 | 0.9500 | 0.9500 | 0.9500 | 0.8571 | 0.3000 | 0.4444 |
| fitness_improvement | 19 | 0.9333 | 0.7368 | 0.8235 | 0.8750 | 0.3684 | 0.5185 |
| hydration_focus | 32 | 0.8857 | 0.9688 | 0.9254 | 0.8158 | 0.9688 | 0.8857 |
| sleep_focus | 56 | 0.9643 | 0.9643 | 0.9643 | 0.9636 | 0.9464 | 0.9550 |
| weight_management | 64 | 0.9242 | 0.9531 | 0.9385 | 0.8429 | 0.9219 | 0.8806 |

Confusion matrices and their label order are in analysis.json; every prediction and noisy-label disagreement is in error_analysis.csv.


## Reliability, structured output and safety screening

- Final case statuses: `{"ok": 189, "invalid_output": 9, "provider_error": 2}`.
- First-attempt statuses: `{"ok": 142, "transport_error": 7, "provider_error": 44, "invalid_output": 7}`.
- API attempts: **266**, including **66** retries.
- HTTP attempt statuses: `{"200": 198, "transport": 9, "503": 59}`.
- Strict schema-valid outputs: **189/200**.
- Limited automated suggestion safety flags: **0**.

The parser rejects unknown categories, extra fields, non-JSON text, empty/oversized
text and invalid suggestion lists. Raw outputs and finish reasons are retained;
truncated/provider-blocked output is not silently repaired. Screen flags only cover
some medication-change, diagnosis and extreme-diet wording in suggestions. Zero
flags is not a safety pass. Provider safety ratings may be absent. No independent
human/clinical review or adversarial allergy/medication/urgent-symptom evaluation
was performed. Those constraints are absent from this numeric benchmark.

## Measured latency and cost estimate

| Measurement | N | Median ms | p95 ms |
| --- | --- | --- | --- |
| ml | 200 | 33.276 | 42.173 |
| rule | 200 | 0.002 | 0.003 |
| llm_successful_case_including_retries | 189 | 6736.008 | 29142.773 |
| llm_all_attempts | 266 | 4098.042 | 21152.308 |
| llm_successful_attempts | 189 | 4658.724 | 18418.679 |

ML/rule timings are local compute after model warmup, excluding HTTP and feature
construction. LLM timings include HTTP/provider processing; successful-case totals
include retries/backoff. The API client reuses connections. These are operational
latencies on different infrastructure, not a controlled hardware speed comparison.
Local ML measurements were taken between provider requests; machine load can vary.

Returned usage across all recorded attempts: `{"promptTokenCount": 87577, "candidatesTokenCount": 28804, "thoughtsTokenCount": 0, "cachedContentTokenCount": 0, "totalTokenCount": 116381}`.
**68** attempts had no usage metadata. At the published
standard paid text rates ($0.30/M input, $0.03/M cached input, $2.50/M output including
thinking), known usage estimates **$0.098283**
for the run, or **$0.00049142 per case**.
Rates verified 2026-10-16: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).
This is **not the actual bill**: account tier, credits and failed-request billing are
unknown. Diagnostics, smoke tests, initial failed run and errors without usage are
excluded from this estimate. Local ML/rule financial cost was not measured, not zero.

## Subjective evaluation — separate from the metrics above

The predeclared rubric scores relevance, personalization, actionable specificity,
completeness and clarity separately: 0 absent/contradictory, 1 partial/generic,
2 clear/profile-grounded. Safety is concern/no concern observed/uncertain. No total
score is calculated. The first two CSV cases of each reference class form a fixed
12-case review sample; this is exploratory and not representative human validation.
ML category-only outputs are not scored on narrative dimensions.

Reviewer: Codex assistant; not an independent human or clinical evaluator. Method: Exploratory, unblinded inspection of the predeclared first two CSV cases per reference class (12 cases). Read actual profiles, categories, rationales and suggestions; invalid output is unrated, not silently removed. Scores are subjective observations, not measured ground truth.

| Case | Relevance | Personalization | Specificity | Completeness | Clarity | Safety observation |
| --- | --- | --- | --- | --- | --- | --- |
| case-000 | 2 | 1 | 1 | 1 | 2 | uncertain |
| case-001 | 2 | 1 | 2 | 2 | 2 | no concern observed |
| case-002 | 2 | 2 | 1 | 2 | 2 | no concern observed |
| case-003 | 2 | 1 | 1 | 1 | 2 | no concern observed |
| case-005 | 2 | 1 | 2 | 1 | 2 | uncertain |
| case-006 | 0 | 1 | 2 | 1 | 1 | uncertain |
| case-007 | 2 | 1 | 2 | 1 | 2 | no concern observed |
| case-008 | 1 | 1 | 0 | 1 | 2 | concern |
| case-009 | 2 | 1 | 2 | 1 | 2 | uncertain |
| case-010 | 2 | 1 | 2 | 2 | 2 | no concern observed |
| case-013 | 2 | 1 | 2 | 2 | 2 | no concern observed |
| case-032 | Not rated | Not rated | Not rated | Not rated | Not rated | not rated |

The inspected narratives were usually clear and practical but largely reused category-level advice. Case-006 exposed a concrete AND/boundary reasoning error. Case-008 gave broader healthy-profile reassurance than the synthetic task supports. Cases involving minors or extreme BMI warrant qualified review; no automated keyword match would establish safety. Case-032 failed the output contract and was not repaired. This small, unblinded assistant review cannot support an ML-versus-LLM narrative-quality ranking or a clinical safety conclusion.


Independent blinded human ratings, inter-rater agreement and clinical safety review
remain pending. Repeated generation consistency was not measured; technical retries
after no returned answer are not repeatability experiments. The model name is not
an immutable snapshot and sampling is not controlled, so future outputs may vary.

## Conclusions by dimension

On this run, the saved ML model correctly classified 186/200 cases versus 162/200
for the LLM with failures counted as incorrect: a 12-percentage-point advantage.
The LLM returned 189 valid outputs; its valid-only accuracy was 162/189 (85.71%).
This is evidence for this synthetic task and run, not general superiority. The direct
rule baseline is an interpretable reference for this known rule-generated task.
ML provides fast local category predictions; the LLM also produces narrative guidance
at greater measured network latency and provider dependency. Narrative usefulness
and safety cannot be ranked against a classifier's category-only output. No system
is declared universally better and no result establishes clinical validity.

## Evidence and exact commands

Evidence: [summary.json](ml_evidence/benchmark-gemini35-v3/summary.json), [analysis.json](ml_evidence/benchmark-gemini35-v3/analysis.json), [outputs.jsonl](ml_evidence/benchmark-gemini35-v3/outputs.jsonl), [results.csv](ml_evidence/benchmark-gemini35-v3/results.csv), [error_analysis.csv](ml_evidence/benchmark-gemini35-v3/error_analysis.csv), [failures_and_retries.json](ml_evidence/benchmark-gemini35-v3/failures_and_retries.json), [review_sample.json](ml_evidence/benchmark-gemini35-v3/review_sample.json), [prompt.txt](ml_evidence/benchmark-gemini35-v3/prompt.txt).

From the repository root (PowerShell); use NEW output paths to preserve recorded runs:

```powershell
Set-Location ai-ml
.\.venv\Scripts\python.exe -m app.evaluation.diagnose_gemini --output ../docs/ml_evidence/gemini-diagnostic-live.json
.\.venv\Scripts\python.exe -m app.evaluation.benchmark --run-dir models/cep-20k-v1 --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir ../docs/ml_evidence/benchmark-gemini35-v3 --llm --llm-model gemini-3.5-flash-lite --interval-seconds 1 --max-transient-retries 2
.\.venv\Scripts\python.exe -m app.evaluation.analyze_benchmark --run-dir ../docs/ml_evidence/benchmark-gemini35-v3
Set-Location ..
.\ai-ml\.venv\Scripts\python.exe scripts/report-benchmark.py --run-dir docs/ml_evidence/benchmark-gemini35-v3
npm run test:ml
```

These are the actual diagnostic/primary-analysis commands; their output paths already
exist and must be changed to rerun API requests. The analysis/report commands can be
rerun without API access. The runner checks the saved model path and all split checks
before every run. The initial sandbox diagnostic recorded ConnectError; an approved
network-enabled diagnostic obtained the actual provider responses. No API key is
printed or included in saved payloads. The actual application configuration continues
to reference its existing model; this task does not fix or activate that configuration.
