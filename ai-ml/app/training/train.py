import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from app.config import METADATA_PATH, MODEL_PATH
from app.evaluation.metrics import evaluate_model
from app.features.engineering import FEATURE_DESCRIPTIONS, FEATURE_NAMES
from app.preprocessing.pipeline import build_dataframe
from app.training.dataset import generate_dataset
from app.preprocessing.validation import validate_raw, validate_features, load_feature_dataset, assert_disjoint

logger = logging.getLogger("train_model")

MODEL_PARAMS = {
    "n_estimators": 200,
    "max_depth": 12,
    "min_samples_leaf": 3,
    "class_weight": "balanced",
    "random_state": 42,
}


def train(n_samples: int = 3000, test_size: float = 0.2, extra_rows=None, extra_labels=None, seed: int = 42):
    """Historical generator baseline; not used for candidate selection or promotion."""
    rows, labels = generate_dataset(n_samples, seed=seed)
    if extra_rows:
        raise ValueError("Feedback labels need independent review and a frozen evaluation set; automatic feedback training is disabled")

    X = build_dataframe(rows)
    y = labels
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    model = RandomForestClassifier(**{**MODEL_PARAMS, "random_state": seed})
    model.fit(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)
    importances = dict(zip(
        FEATURE_NAMES,
        [round(float(v), 4) for v in model.feature_importances_],
    ))
    metadata = {
        "model_type": "RandomForestClassifier",
        "model_params": {**MODEL_PARAMS, "random_state": seed},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "data_source": "synthetic demo dataset (ai-ml/app/training/dataset.py) - not real medical data",
        "features": FEATURE_NAMES,
        "feature_descriptions": FEATURE_DESCRIPTIONS,
        "feature_importances": importances,
        "classes": list(model.classes_),
        "metrics": {k: metrics[k] for k in ("accuracy", "precision", "recall", "f1")},
        "confusion_matrix": metrics["confusion_matrix"],
        "confusion_labels": metrics["labels"],
    }
    return model, metadata, metrics


def save(model, metadata, model_path=None, metadata_path=None):
    model_path = Path(model_path or MODEL_PATH)
    metadata_path = Path(metadata_path or METADATA_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve any previous artifacts before an explicitly requested save.
    import shutil
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for path in (model_path, metadata_path):
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + "." + stamp + ".bak"))
    joblib.dump(model, model_path)
    metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Saved model -> %s", model_path)


def split_indices(y, seed=42):
    import numpy as np
    indices = np.arange(len(y))
    development, test = train_test_split(indices, test_size=.2, random_state=seed, stratify=y)
    training, validation = train_test_split(development, test_size=.25, random_state=seed, stratify=y.iloc[development])
    return {"train": training, "validation": validation, "test": test}


def run_experiment(dataset, benchmark, output_dir, seed=42):
    """Select on validation only; the test set is evaluated once after selection."""
    import hashlib
    import importlib.metadata
    import io
    import time
    import numpy as np
    import pandas as pd
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    output = Path(output_dir)
    if output.exists():
        raise ValueError(f"Output directory already exists; choose a new run directory: {output}")
    X, y = load_feature_dataset(dataset)
    bench = pd.read_csv(benchmark)
    for row in bench.to_dict("records"):
        validate_raw(row)
    bx = validate_features(build_dataframe(bench.to_dict("records")))
    assert_disjoint(X, bx)
    splits = split_indices(y, seed)
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert_disjoint(X.iloc[splits[a]], X.iloc[splits[b]])
    tr, va, te = (splits[k] for k in ("train", "validation", "test"))
    candidates = {
        "dummy": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=seed)),
        "random_forest": RandomForestClassifier(**{**MODEL_PARAMS, "random_state": seed}),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15,
             l2_regularization=1, early_stopping=False, random_state=seed),
    }
    scores = {}
    for name, model in candidates.items():
        started = time.perf_counter()
        model.fit(X.iloc[tr], y.iloc[tr])
        elapsed = time.perf_counter() - started
        metrics = evaluate_model(model, X.iloc[va], y.iloc[va])
        model.predict(X.iloc[va[:1]])  # warmup
        latency = []
        for index in va[:100]:
            row = X.iloc[[index]]
            started = time.perf_counter()
            model.predict(row)
            latency.append((time.perf_counter() - started) * 1000)
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        scores[name] = {"validation_metrics": metrics, "training_seconds": elapsed,
                       "single_prediction_ms_p50": float(np.median(latency)),
                       "single_prediction_ms_p95": float(np.percentile(latency, 95)),
                       "serialized_bytes": buffer.tell(), "params": {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in model.get_params().items()}}
    selected = max(scores, key=lambda name: scores[name]["validation_metrics"]["macro_f1"])
    model = candidates[selected]  # No refit: deploy exactly the model evaluated on test.
    metrics = evaluate_model(model, X.iloc[te], y.iloc[te])
    metadata = {
        "model_type": type(model).__name__, "selected_candidate": selected,
        "model_params": scores[selected]["params"], "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X), "n_train": len(tr), "n_validation": len(va), "n_test": len(te),
        "seed": seed, "features": FEATURE_NAMES, "feature_descriptions": FEATURE_DESCRIPTIONS,
        "classes": list(model.classes_), "metrics": metrics,
        "confusion_matrix": metrics["confusion_matrix"], "confusion_labels": metrics["labels"],
        "feature_importances": dict(zip(FEATURE_NAMES, map(float, model.feature_importances_))) if hasattr(model, "feature_importances_") else {},
        "data_source": "CEP synthetic wellness v1; rule labels with noise, not clinical evidence",
        "dataset": {"path": str(Path(dataset).resolve()), "sha256": hashlib.sha256(Path(dataset).read_bytes()).hexdigest()},
        "benchmark": {"path": str(Path(benchmark).resolve()), "sha256": hashlib.sha256(Path(benchmark).read_bytes()).hexdigest()},
        "versions": {n: importlib.metadata.version(n) for n in ("numpy", "pandas", "scikit-learn", "joblib")},
        "selection": "highest validation macro F1; fixed 60/20/20 stratified split; no test-based tuning or refit",
        "preprocessing": "existing 14 engineered features; StandardScaler fitted on training only for logistic candidate",
    }
    output.mkdir(parents=True)
    save(model, metadata, output / "model.pkl", output / "feature_metadata.json")
    (output / "experiment.json").write_text(json.dumps({"candidates": scores, "selected": selected, "test_metrics": metrics}, indent=2))
    assignments = pd.DataFrame({"row_index": np.arange(len(X)), "split": "", "profile_sha256": [hashlib.sha256(row.astype(float).to_numpy().tobytes()).hexdigest() for _, row in X.iterrows()]})
    for name, ids in splits.items():
        assignments.loc[ids, "split"] = name
    assignments.to_csv(output / "splits.csv", index=False)
    metadata["model_sha256"] = hashlib.sha256((output / "model.pkl").read_bytes()).hexdigest()
    metadata["splits_sha256"] = hashlib.sha256((output / "splits.csv").read_bytes()).hexdigest()
    (output / "feature_metadata.json").write_text(json.dumps(metadata, indent=2))
    pd.DataFrame({"row_index": te, "reference": y.iloc[te], "prediction": model.predict(X.iloc[te])}).to_csv(output / "test_predictions.csv", index=False)
    return metadata


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Engineered CSV with wellness_category")
    parser.add_argument("--benchmark", required=True, help="Separate raw benchmark CSV for leakage guard")
    parser.add_argument("--output-dir", required=True, help="New run directory under models/")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = run_experiment(args.dataset, args.benchmark, args.output_dir, args.seed)
    print(json.dumps({"selected": result["selected_candidate"], "metrics": result["metrics"]}, indent=2))
