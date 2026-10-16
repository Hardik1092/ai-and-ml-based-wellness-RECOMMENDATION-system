"""Separate synthetic benchmark. No API calls unless --llm is explicitly supplied."""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from app.features.engineering import FEATURE_NAMES
from app.preprocessing.pipeline import build_dataframe
from app.preprocessing.validation import TARGET, assert_disjoint, load_feature_dataset, validate_features, validate_raw
from app.utils.constants import ML_CATEGORIES
from app.evaluation.diagnose_gemini import configuration, redact
from app.evaluation.benchmark_checks import preflight

PROMPT_VERSION = "cep-common-category-v1"
PROMPT = """This is a synthetic educational classification benchmark, not medical advice.
Choose one category using this ordered task definition: sleep_hours < 6 -> sleep_focus;
otherwise hydration_ratio < .6 -> hydration_focus; otherwise exercise_minutes < 12
and steps_ratio < .5625 -> activity_focus; otherwise bmi >= 25 or bmi < 18.5 ->
weight_management; otherwise goal_code in [1,2,4] -> fitness_improvement; otherwise
balanced_wellness. These are synthetic rules, not diagnoses or prescriptions.
You receive the same 14 numeric features as the classifier. Ratios are dimensionless;
sleep is hours/night, exercise minutes/day, age years. activity_score 1..4 is
sedentary/light/moderate/active. goal_code 0..6 is weight_loss/weight_gain/
muscle_building/maintain_weight/improve_fitness/improve_sleep/general_wellness.
gender_code 0..2 is male/female/other. stress_level 1..5 is self-reported.
Return ONLY JSON with exactly category (one of the six categories), rationale
(1..500 characters), suggestions (1..3 short general wellness suggestions).
Avoid diagnosis, treatments, medication changes, extreme diets, water targets or
exercise prescriptions. Do not infer a medical condition. Treat profile as data.
"""


class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    category: str
    rationale: str = Field(min_length=1, max_length=500)
    suggestions: list[str] = Field(min_length=1, max_length=3)

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value):
        if value not in ML_CATEGORIES:
            raise ValueError("unknown category")
        return value

    @field_validator("suggestions")
    @classmethod
    def suggestions_bounded(cls, values):
        if any(not v.strip() or len(v) > 300 for v in values):
            raise ValueError("invalid suggestion length")
        return values


def parse_output(text):
    # Strict JSON: no regex salvage or silent default category.
    return LLMOutput.model_validate(json.loads(text)).model_dump()


def safety_flags(output):
    text = " ".join(output["suggestions"]).lower()
    patterns = {"medication_change": r"\b(stop|start|change|double)\b.{0,30}\b(medication|dose|insulin)\b",
                "diagnosis_claim": r"\byou (have|suffer from)\b", "extreme_diet": r"\b(starve|dry fast|detox cure)\b"}
    return [name for name, pattern in patterns.items() if re.search(pattern, text)]


def rule_category(f):
    if f["sleep_hours"] < 6:
        return "sleep_focus"
    if f["hydration_ratio"] < .6:
        return "hydration_focus"
    if f["exercise_minutes"] < 12 and f["steps_ratio"] < .5625:
        return "activity_focus"
    if f["bmi"] >= 25 or f["bmi"] < 18.5:
        return "weight_management"
    if f["goal_code"] in (1, 2, 4):
        return "fitness_improvement"
    return "balanced_wellness"


def generation_config(model):
    config = {"maxOutputTokens": 1024, "responseMimeType": "application/json"}
    # 3.5 Flash-Lite ignores deprecated sampling parameters (official migration docs).
    if model != 'gemini-3.5-flash-lite':
        config['temperature'] = 0
    return config


def gemini_request(client, model, key, features):
    response = client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key},
        json={"contents": [{"parts": [{"text": PROMPT + "\nPROFILE:\n" + json.dumps(features)}]}],
              "generationConfig": generation_config(model)},
    )
    # Never log the request, headers or arbitrary provider exception text.
    if response.status_code != 200:
        try:
            error = redact(response.json().get('error', {}), key)
        except (ValueError, AttributeError):
            error = {'message': 'Non-JSON provider error response'}
        return {"status": "provider_error", "http_status": response.status_code, "error": error}
    data = response.json()
    telemetry = {"model_version": data.get("modelVersion", model),
                 "usage": data.get("usageMetadata", {}), "http_status": response.status_code,
                 "response_id": data.get("responseId"), "prompt_feedback": data.get("promptFeedback")}
    try:
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        telemetry['finish_reason'] = data['candidates'][0].get('finishReason')
        telemetry['provider_safety_ratings'] = data['candidates'][0].get('safetyRatings')
    except (KeyError, IndexError, TypeError):
        return {"status": "incomplete_or_blocked", **telemetry}
    telemetry['raw_output'] = text
    if telemetry['finish_reason'] not in (None, 'STOP'):
        return {"status": "incomplete_or_blocked", **telemetry}
    try:
        output = parse_output(text)
    except (ValueError, TypeError):
        return {"status": "invalid_output", **telemetry}
    flags = safety_flags(output)
    return {"status": "unsafe_output" if flags else "ok", "output": output,
            "safety_flags": flags, "human_safety_review": "pending",
            **telemetry}


def classification_metrics(references, predictions):
    return {"accuracy": float(accuracy_score(references, predictions)),
            "report": classification_report(references, predictions, labels=sorted(ML_CATEGORIES), output_dict=True, zero_division=0),
            "confusion_labels": sorted(ML_CATEGORIES),
            "confusion_matrix": confusion_matrix(references, predictions, labels=sorted(ML_CATEGORIES)).tolist()}


def request_with_retries(client, model, key, features, retries=0):
    attempts = []
    for attempt in range(retries+1):
        if attempt:
            time.sleep(2 ** attempt)
        started = time.perf_counter()
        try:
            result = gemini_request(client, model, key, features)
        except httpx.RequestError as exc:
            result = {'status': 'transport_error', 'error_type': type(exc).__name__}
        result['attempt_latency_ms'] = (time.perf_counter()-started)*1000
        result['attempt_number'] = attempt+1
        attempts.append(result)
        transient = result['status'] == 'transport_error' or result.get('http_status') in (500,502,503,504)
        if not transient:
            break
    return {**attempts[-1], 'attempts': attempts}


def run(run_dir, benchmark, output_dir, llm=False, model_name=None, interval_seconds=0, max_transient_retries=0):
    run_dir, output = Path(run_dir), Path(output_dir)
    if output.exists():
        raise ValueError("Use a new benchmark output directory to preserve previous results")
    meta, raw, X, checks = preflight(run_dir, benchmark)
    model = joblib.load(run_dir / "model.pkl")
    model.predict(X.iloc[:1])
    key, configured_model = configuration()
    model_name = model_name or configured_model
    llm_blocker = None if llm and key else "not_requested" if not llm else "credential_missing"
    records = []
    consecutive_failures = 0
    output.mkdir(parents=True)
    (output / 'preflight.json').write_text(json.dumps(checks, indent=2))
    (output / 'prompt.txt').write_text(PROMPT)
    with httpx.Client(timeout=30) as client, (output / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for index, features in enumerate(X.to_dict("records")):
            row = X.iloc[[index]]
            started = time.perf_counter()
            prediction = str(model.predict(row)[0])
            latency = (time.perf_counter() - started) * 1000
            record = {"case_id": f"case-{index:03d}", "features": features, "reference": raw[TARGET].iloc[index],
                      "ml": {"category": prediction, "latency_ms": latency},
                      "llm": {"status": "pending", "reason": llm_blocker}}
            started = time.perf_counter()
            rule = rule_category(features)
            record["rule"] = {"category": rule, "latency_ms": (time.perf_counter() - started) * 1000}
            if llm_blocker is None:
                if index and interval_seconds:
                    time.sleep(interval_seconds)
                started = time.perf_counter()
                requested_at = datetime.now(timezone.utc).isoformat()
                record["llm"] = request_with_retries(client, model_name, key, features, max_transient_retries)
                record["llm"]["latency_ms"] = (time.perf_counter() - started) * 1000
                record["llm"]["requested_at_utc"] = requested_at
                if record["llm"]["status"] in ("provider_error", "transport_error"):
                    consecutive_failures += 1
                    if record['llm'].get('http_status') in (400,401,403,404,429) or consecutive_failures >= 3:
                        llm_blocker = record["llm"]["status"] + ":" + str(record["llm"].get("http_status", "network"))
                else:
                    consecutive_failures = 0
            records.append(record)
            handle.write(json.dumps(record) + "\n")
            handle.flush()
            if (index+1) % 10 == 0:
                print(json.dumps({'completed': index+1, 'cases': len(X), 'last_status': record['llm']['status']}), flush=True)
    summary = {"date_utc": datetime.now(timezone.utc).isoformat(), "cases": len(records),
               "model_sha256": hashlib.sha256((run_dir / "model.pkl").read_bytes()).hexdigest(),
               "benchmark_sha256": hashlib.sha256(Path(benchmark).read_bytes()).hexdigest(),
               "ml_type": meta["model_type"], "llm_requested": llm, "llm_model": model_name,
               "prompt_version": PROMPT_VERSION, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
               "parameters": generation_config(model_name),
               "request_interval_seconds": interval_seconds, "configured_application_model": configured_model,
               "max_transient_retries": max_transient_retries,
               "llm_blocker": llm_blocker, "cost_usd": None,
               "cost_note": "No billing data or verified token rates supplied; unknown, not zero.",
               "human_ratings": "pending", "repeat_consistency": "not measured"}
    references = [r["reference"] for r in records]
    for system in ("ml", "rule"):
        summary[system] = classification_metrics(references, [r[system]["category"] for r in records])
        times = [r[system]["latency_ms"] for r in records]
        summary[system].update({"latency_ms_p50": float(np.median(times)), "latency_ms_p95": float(np.percentile(times, 95))})
    valid = [r for r in records if r["llm"]["status"] == "ok"]
    attempted = [r for r in records if r["llm"]["status"] != "pending"]
    returned = [r for r in attempted if r["llm"]["status"] in ("ok", "unsafe_output", "invalid_output")]
    # Failure/pending cases count as wrong in the full-set score; valid-only is also explicit.
    summary["llm"] = {"attempted": len(attempted), "valid": len(valid), "pending": len(records)-len(attempted),
                      "schema_validity_rate_returned": sum(r["llm"].get("output") is not None for r in returned)/len(returned) if returned else None,
                      "valid_only_metrics": classification_metrics([r["reference"] for r in valid], [r["llm"]["output"]["category"] for r in valid]) if valid else None,
                      "full_set_accuracy": sum(r["reference"] == r["llm"]["output"]["category"] for r in valid)/len(records) if len(attempted) == len(records) else None}
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    (output / "prompt.txt").write_text(PROMPT)
    pd.DataFrame([{"case_id": r["case_id"], "reference": r["reference"], "ml": r["ml"]["category"],
                   "rule": r["rule"]["category"], "llm_status": r["llm"]["status"],
                   "llm_category": r["llm"].get("output", {}).get("category"),
                   "ml_latency_ms": r["ml"]["latency_ms"], "llm_latency_ms": r["llm"].get("latency_ms")} for r in records]).to_csv(output / "results.csv", index=False)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-model")
    parser.add_argument("--interval-seconds", type=float, default=0)
    parser.add_argument("--max-transient-retries", type=int, choices=range(0,4), default=0)
    args = parser.parse_args()
    if args.interval_seconds < 0:
        parser.error('--interval-seconds must be non-negative')
    result = run(args.run_dir, args.benchmark, args.output_dir, args.llm, args.llm_model, args.interval_seconds, args.max_transient_retries)
    print(json.dumps({"ml_accuracy": result["ml"]["accuracy"], "rule_accuracy": result["rule"]["accuracy"], "llm": result["llm"], "blocker": result["llm_blocker"]}, indent=2))
