# Frozen protocol before the working-model run — 2026-10-16

ML artifact: cep-20k-v1, SHA-256 4d131cc7cbd2b8350cc1338adf8cc2f6447a6f3b889feb18b8e4fe7b0ef7729e.
Benchmark: original 200 cases, SHA-256 43f02e05885381a736c4905322c5a2816c9fcf2c2e7e0ccb1da1dbd8fa41661a.
Preflight must pass model/data/split/benchmark checksums, reproduce split membership,
and detect zero exact/defined-near benchmark overlap with train, validation and test.
The model was selected using validation macro F1; benchmark was only used for leakage
checking during training, never fit, scored or used to select candidate parameters.

Task: the existing `cep-common-category-v1` prompt, unchanged. Both systems receive
the same 14 engineered values. The LLM gets explicit rule definitions; ML learned
noisy synthetic labels. This compares synthetic rule imitation, not independent
wellness reasoning or complete nutrition/activity plans. Reference-label agreement
and deterministic-rule compliance will be reported separately.

Select Gemini 2.5 Flash-Lite from the actual v1beta models listing, because it is a
stable low-cost text model supporting generateContent. Verify one non-benchmark
seed-91821 profile first. Access/compatibility failures may require another listed
model, with every attempt recorded; do not choose models by benchmark scores.
Application env/config/model files stay unchanged. Use explicit CLI model override.
Temperature 0, max output tokens 1024, JSON MIME mode, 30-second timeout. No prompt
changes, automatic repair, best-of-N output selection, or hidden retries. Preserve
each raw response, usage, version, finish reason, latency and error. Stop on provider
or transport failure rather than spending requests under a persistent account error.

Quantitative: reference accuracy, macro/weighted/per-class F1, confusion matrix;
rule compliance; JSON/schema validity; failure/pending counts; automated safety flag
rate; median/p95 client latency. ML latency excludes network, LLM includes network;
do not interpret this as equal hardware efficiency. Record token usage and estimate
cost only with dated provider rates; billing/tier unknown means actual cost unknown.

Safety screen: existing limited keyword rules, applied to suggestions; counts are
screening results, never proof of safety. Human clinical review is not available.

Subjective rubric: relevance, personalization, actionable specificity, completeness,
clarity each 0 (absent/contradictory), 1 (partial/generic), 2 (clear/profile-grounded).
Safety: concern/no concern observed/uncertain, never a clinical assurance. If an
assistant review is included, use the first two cases of each reference class in
CSV order (12 preselected examples), disclose that it is unblinded and not independent
human evaluation. Do not give ML category-only outputs narrative scores. No composite
score and no universal winner. Independent blinded human review remains pending.

Repeatability: the primary run is one response per profile. Optional repeat checks,
if performed, must be reported separately and not replace primary outputs. Otherwise
state not measured. Synthetic benchmark lacks allergies/medications/urgent symptoms
and cannot validate those live application safety constraints.

## Access-driven amendment before primary run

The live model list included 2.5 Flash-Lite, but a real request returned 404:
"This model models/gemini-2.5-flash-lite is no longer available to new users."
The response recommended gemini-3.5-flash-lite, which also appears in the live model
list with generateContent support. The same non-benchmark seed-91821 smoke profile
succeeded with 3.5 Flash-Lite. Select **gemini-3.5-flash-lite** for the primary run,
solely on access/compatibility, not on benchmark scores. Actual response version is
recorded per case; listing version is 3.5-flash-lite-07-2026.

Official migration documentation says temperature/top_p/top_k are ignored for this
model. Omit them; do not claim temperature=0 or deterministic generation. Keep the
prompt and 1024-token limit unchanged, with JSON MIME mode and default thinking.
Source: https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6

Run one sequential request per case with one second between cases, no retries. A
30-second timeout or provider error is recorded and halts further calls. This limits
uncontrolled spending and exposes real access failures. Rate-based cost estimate
uses standard text rates $0.30/M input and $2.50/M output from Google's pricing page
(accessed 2026-10-16), with actual charged cost separately unknown.

## Transient-availability amendment

The first primary attempt returned HTTP 503 before producing any benchmark output:
"This model is currently experiencing high demand." Preserve that failed run in
benchmark-gemini35-v2. For the new full run, allow at most TWO retries after transport
errors or HTTP 500/502/503/504, with 2- and 4-second backoff. Never retry invalid,
unsafe or incorrect generated outputs. Record every attempt, first-attempt status,
usage and latency plus total case time including retries. Stop immediately for
400/401/403/404/429, or after three consecutive exhausted transient failures.
This is technical failure recovery, not best-of-N answer selection. Report both
first-attempt and eventual completion rates so retries do not conceal reliability.
