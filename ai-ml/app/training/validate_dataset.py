"""Reproduce package claims and explicitly quantify exact/near profile overlap."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from app.features.engineering import FEATURE_NAMES
from app.preprocessing.pipeline import build_dataframe
from app.preprocessing.validation import TARGET, load_feature_dataset, validate_raw, validate_features
from app.training.dataset import generate_dataset, label_row
from app.training.train import split_indices

# Operational near-duplicate definition: same categorical codes and within these
# tolerances on EVERY continuous coordinate (Chebyshev distance <= 1).
TOLERANCES = {"bmi": .1, "age": .5, "activity_score": .1, "sleep_hours": .1,
              "sleep_adequacy": .1, "hydration_ratio": .01, "hydration_adequacy": .1,
              "exercise_minutes": 1, "exercise_adequacy": .1, "steps_ratio": .01,
              "calorie_ratio": .01, "stress_level": .1, "goal_code": .1, "gender_code": .1}


def overlap(left, right):
    scale = np.array([TOLERANCES[n] for n in FEATURE_NAMES])
    nearest = NearestNeighbors(n_neighbors=1, metric="chebyshev", algorithm="kd_tree").fit(left[FEATURE_NAMES].to_numpy() / scale)
    distances, _ = nearest.kneighbors(right[FEATURE_NAMES].to_numpy() / scale)
    return {"exact": int((distances[:, 0] == 0).sum()), "near_including_exact": int((distances[:, 0] <= 1).sum()), "minimum_scaled_distance": float(distances.min())}


def inspect(package, feature_path, seed=42):
    package = Path(package)
    files = [*package.glob("*.csv"), Path(feature_path), Path(__file__).resolve().parents[2] / "data/sample_training_data.csv"]
    result = {"files": {}, "near_duplicate_tolerances": TOLERANCES}
    for path in files:
        df = pd.read_csv(path)
        result["files"][str(path)] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "shape": list(df.shape), "dtypes": {k: str(v) for k, v in df.dtypes.items()},
            "missing_by_column": df.isna().sum().to_dict(), "duplicate_rows": int(df.duplicated().sum()),
            "classes": df[TARGET].value_counts().to_dict(),
            "ranges": {n: {"min": float(df[n].min()), "max": float(df[n].max())} for n in df.select_dtypes("number")}}
    X, y = load_feature_dataset(feature_path)
    raw = pd.read_csv(package / "cep_synthetic_wellness_20000.csv")
    bench = pd.read_csv(package / "cep_ml_llm_benchmark_cases_200.csv")
    for row in [*raw.to_dict("records"), *bench.to_dict("records")]:
        validate_raw(row)
    rebuilt = validate_features(build_dataframe(raw.to_dict("records")))
    bx = validate_features(build_dataframe(bench.to_dict("records")))
    if not bench[TARGET].isin(y.unique()).all():
        raise ValueError("Unknown benchmark label")
    generated_rows, generated_y = generate_dataset(len(raw), seed=42)
    result.update({
        "feature_mismatch_cells": int((abs(rebuilt - X) > 1e-9).sum().sum()),
        "raw_feature_label_mismatches": int((raw[TARGET] != y).sum()),
        "generator_seed42_features_match": bool(np.allclose(build_dataframe(generated_rows), rebuilt)),
        "generator_seed42_labels_match": generated_y == raw[TARGET].tolist(),
        "benchmark_seed2026_reproduced": bool(np.allclose(build_dataframe(generate_dataset(200, seed=2026)[0]), bx)) and generate_dataset(200, seed=2026)[1] == bench[TARGET].tolist(),
        "rule_disagreements": int((raw.apply(label_row, axis=1) != raw[TARGET]).sum()),
        "benchmark_rule_disagreements": int((bench.apply(label_row, axis=1) != bench[TARGET]).sum()),
        "benchmark_overlap": overlap(X, bx),
        "copy_matches_package": Path(feature_path).read_bytes() == (package / "cep_ml_features_20000.csv").read_bytes(),
        "synthetic_extremes": {"age_under18": int((raw.age < 18).sum()), "bmi_under16": int((raw.bmi < 16).sum()), "bmi_over40": int((raw.bmi > 40).sum())},
        "raw_category_counts": {n: raw[n].value_counts().to_dict() for n in ("gender", "goal", "activity_level")},
    })
    splits = split_indices(y, seed)
    result["split_counts"] = {n: {"rows": len(ids), "classes": y.iloc[ids].value_counts().to_dict()} for n, ids in splits.items()}
    result["split_overlap"] = {a + "_vs_" + b: overlap(X.iloc[splits[a]], X.iloc[splits[b]]) for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))}
    # Original generated baseline shares seed/prefix with the package: explicitly report.
    legacy = build_dataframe(generate_dataset(3000)[0])
    result["legacy_generator_overlap_with_20k"] = overlap(X, legacy)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = inspect(args.package, args.dataset)
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("files", "raw_category_counts")}, indent=2))
