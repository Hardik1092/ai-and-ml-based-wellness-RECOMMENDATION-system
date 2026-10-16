# Open follow-up findings after ML activation

These were **not fixed** by activating `cep-20k-v1`. The original evidence remains in
[ML_RUNTIME_VERIFICATION_REPORT.md](ML_RUNTIME_VERIFICATION_REPORT.md).

## Zero-value preprocessing — fixed in source, regression verified

The subsequent [zero-value fix report](ZERO_VALUE_PREPROCESSING_REPORT.md) records
the narrow backend/Python correction and passing tests. Existing long-lived services
need a deliberate restart to load the changed source; this phase did not restart them.
The following description preserves the original finding:

`backend/src/services/featureBuilder.js` uses `avg_sleep || profile.sleep_hours`
and `avg_water || profile.water_intake_ml`. A legitimate zero log is therefore
replaced by a profile value. Zero calories also become a target-equivalent ratio
through `raw.calories || calorieTarget` in backend and Python feature construction.
The previous synthetic reproduction changed zero sleep to 8 h, zero water to
hydration ratio 0.949, and zero calories to ratio 1.

Recommended separate fix: distinguish missing values from zero, preserve backend/
Python parity, add focused boundary regressions, and assess feature-distribution
compatibility before changing inference semantics. No preprocessing changes or
retraining were made in this activation task.

Separately, the activation API test confirmed that posting `sleep:null` to an
existing daily log retains its earlier sleep value: `createLog()` intentionally
updates only non-null fields. That retained 8 h log takes precedence over a profile
updated to 5 h. This explains an unchanged prediction; it is not a model cache issue.

## LLM dietary enforcement — OPEN

Catalog nutrition filtering enforces preference/allergy rules before ML ranking.
The separate LLM narrative uses `validateLlmOutput(parsed, allergies)`, literal
allergen-text checks and prompts. It receives no dietary preference for deterministic
validation and cannot guarantee ingredient/allergen synonym coverage.

Recommended separate fix: validate structured food/ingredient identities against
dietary constraints before rendering generated suggestions. Prompts alone are
insufficient. External LLM calls were disabled only inside the disposable backend
verification process; application LLM configuration is unchanged. Successful ML
activation does not fix the configured Gemini model's earlier HTTP 404 or establish
LLM dietary compliance.

## Explanation accuracy and operational provenance — OPEN

A uniform food-score bonus may leave relative ranks unchanged even when item text
claims the item was ranked higher. This wording was not changed.

Permanent runtime provenance is also unchanged: the normal metadata endpoint reports
artifact metadata, not a separately recorded loaded path/PID. Activation used a
verification launcher that records the actual loader object in the same single
serving process and correlates its PID with the listening socket. Future deployments
should repeat identity verification; these local results are not remote deployment
or browser-rendering evidence.
