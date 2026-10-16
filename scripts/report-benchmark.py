"""Render the final benchmark report from recorded evidence, without API calls."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join('Not rated' if v is None else str(v) for v in row)+' |' for row in rows])


def render(directory):
    directory=Path(directory).resolve()
    read=lambda name:json.loads((directory/name).read_text())
    analysis,summary,checks=read('analysis.json'),read('summary.json'),read('preflight.json')
    relative=directory.relative_to(ROOT/'docs').as_posix()
    link=lambda filename:f'[{filename}]({relative}/{filename})'
    cost=analysis['cost']
    complete=analysis['run_completed_all_cases']
    report=f'''# Final ML versus LLM comparison — 2026-10-16

Status: **{'All 200 profiles attempted' if complete else 'Incomplete: provider/access failure; see recorded counts'}**.
Saved ML model: `cep-20k-v1` (HistGradientBoostingClassifier). LLM:
`{summary['llm_model']}`, using the existing Gemini `v1beta:generateContent` REST
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
`{json.dumps(analysis['model_versions'])}`. The response does not provide immutable
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
criterion still chooses hist_gradient_boosting. Evidence: {link('preflight.json')}.

Model SHA-256: `{checks['model_sha256']}`.
Benchmark SHA-256: `{checks['benchmark_sha256']}`.

All systems receive the same 14 engineered numeric features; reference labels,
case IDs and raw fields unavailable to the ML model are excluded from LLM input.
Feature construction is the existing stateless pipeline. Prompt
`{summary['prompt_version']}` explicitly provides the ordered synthetic label rules.
ML learned noisy examples of that function. Thus the common task is **synthetic
rule imitation/classification**, not independent wellness reasoning or a comparison
of complete meal/activity plans. The LLM may add short rationale/suggestions, which
have no generated ML narrative counterpart.

Prompt hash: `{summary['prompt_sha256']}`. The prompt was not tuned on this run.
Parameters: `{json.dumps(summary['parameters'])}`. Temperature is omitted because
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

'''
    report+=table(['System','Reference accuracy','Macro F1','Weighted F1','Rule agreement'],[
        [name,f"{m['accuracy']:.4f}",f"{m['macro_f1']:.6f}",f"{m['weighted_f1']:.6f}",f"{m['agreement_with_rules']:.4f}"] for name,m in analysis['metrics'].items() if name!='llm_valid_only'])
    report+=f'''

Reference labels disagree with the deterministic feature-based rules on
**{analysis['reference_rule_disagreements']}/200 cases**. Agreement with noisy labels
and execution of the explicit rule task are distinct outcomes. The deterministic
rule baseline is included to make this limitation visible.

Paired ML/LLM errors: `{json.dumps(analysis['paired_errors'])}`.
The exact McNemar test is a two-sided paired classification comparison; it does not
measure clinical benefit, generalize outside this synthetic sample, or prove
equivalence when non-significant.

Per-class results (precision/recall/F1; macro metrics weight each class equally):

'''
    report+=table(['Class','Support','ML precision','ML recall','ML F1','LLM precision','LLM recall','LLM F1'],[
        [name,int(m['support']),*[f'{m[k]:.4f}' for k in ('precision','recall','f1-score')],
         *[f"{analysis['metrics']['llm']['per_class'][name][k]:.4f}" for k in ('precision','recall','f1-score')]]
        for name,m in analysis['metrics']['ml']['per_class'].items()])
    report+='\n\nConfusion matrices and their label order are in analysis.json; every prediction and noisy-label disagreement is in error_analysis.csv.\n'
    report+=f'''

## Reliability, structured output and safety screening

- Final case statuses: `{json.dumps(analysis['final_status_counts'])}`.
- First-attempt statuses: `{json.dumps(analysis['first_attempt_status_counts'])}`.
- API attempts: **{analysis['total_api_attempts']}**, including **{analysis['extra_retry_attempts']}** retries.
- HTTP attempt statuses: `{json.dumps(analysis['attempt_http_statuses'])}`.
- Strict schema-valid outputs: **{analysis['schema_valid']}/{analysis['cases']}**.
- Limited automated suggestion safety flags: **{analysis['automated_safety_flagged_cases']}**.

The parser rejects unknown categories, extra fields, non-JSON text, empty/oversized
text and invalid suggestion lists. Raw outputs and finish reasons are retained;
truncated/provider-blocked output is not silently repaired. Screen flags only cover
some medication-change, diagnosis and extreme-diet wording in suggestions. Zero
flags is not a safety pass. Provider safety ratings may be absent. No independent
human/clinical review or adversarial allergy/medication/urgent-symptom evaluation
was performed. Those constraints are absent from this numeric benchmark.

## Measured latency and cost estimate

'''
    report+=table(['Measurement','N','Median ms','p95 ms'],[[name,v['count'],f"{v['median_ms']:.3f}",f"{v['p95_ms']:.3f}"] for name,v in analysis['latency'].items() if v])
    report+=f'''

ML/rule timings are local compute after model warmup, excluding HTTP and feature
construction. LLM timings include HTTP/provider processing; successful-case totals
include retries/backoff. The API client reuses connections. These are operational
latencies on different infrastructure, not a controlled hardware speed comparison.
Local ML measurements were taken between provider requests; machine load can vary.

Returned usage across all recorded attempts: `{json.dumps(cost['usage'])}`.
**{cost['attempts_without_usage']}** attempts had no usage metadata. At the published
standard paid text rates ($0.30/M input, $0.03/M cached input, $2.50/M output including
thinking), known usage estimates **${cost['estimated_standard_paid_usd_known_usage']:.6f}**
for the run, or **${cost['estimated_standard_paid_usd_per_case']:.8f} per case**.
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

'''
    review_path=directory/'subjective_review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text())
        report+=f"Reviewer: {review['reviewer']}. Method: {review['method'].rstrip('.')}.\n\n"
        report+=table(['Case','Relevance','Personalization','Specificity','Completeness','Clarity','Safety observation'],[
            [r['case_id'],*[r[k] for k in ('relevance','personalization','specificity','completeness','clarity')],r['safety']] for r in review['ratings']])
        report+='\n\n'+review['interpretation']+'\n'
    else:
        report+='No subjective ratings have been performed. The review sample is provided for independent reviewers.\n'
    report+='''

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

'''
    report+='Evidence: '+', '.join(link(f) for f in ('summary.json','analysis.json','outputs.jsonl','results.csv','error_analysis.csv','failures_and_retries.json','review_sample.json','prompt.txt'))+'.\n\n'
    report+='''From the repository root (PowerShell); use NEW output paths to preserve recorded runs:

```powershell
Set-Location ai-ml
.\\.venv\\Scripts\\python.exe -m app.evaluation.diagnose_gemini --output ../docs/ml_evidence/gemini-diagnostic-live.json
.\\.venv\\Scripts\\python.exe -m app.evaluation.benchmark --run-dir models/cep-20k-v1 --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir ../docs/ml_evidence/benchmark-gemini35-v3 --llm --llm-model gemini-3.5-flash-lite --interval-seconds 1 --max-transient-retries 2
.\\.venv\\Scripts\\python.exe -m app.evaluation.analyze_benchmark --run-dir ../docs/ml_evidence/benchmark-gemini35-v3
Set-Location ..
.\\ai-ml\\.venv\\Scripts\\python.exe scripts/report-benchmark.py --run-dir docs/ml_evidence/benchmark-gemini35-v3
npm run test:ml
```

These are the actual diagnostic/primary-analysis commands; their output paths already
exist and must be changed to rerun API requests. The analysis/report commands can be
rerun without API access. The runner checks the saved model path and all split checks
before every run. The initial sandbox diagnostic recorded ConnectError; an approved
network-enabled diagnostic obtained the actual provider responses. No API key is
printed or included in saved payloads. The actual application configuration continues
to reference its existing model; this task does not fix or activate that configuration.
'''
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    args=parser.parse_args()
    text=render(args.run_dir)
    (ROOT/'docs/CEP_ML_LLM_COMPARISON_REPORT.md').write_text(text,encoding='utf-8')
    print('Wrote final comparison report from saved evidence.')
