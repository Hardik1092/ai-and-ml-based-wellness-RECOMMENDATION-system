import os
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import ML_ENABLED, ML_PORT, ROOT
from app.features.engineering import FEATURE_DESCRIPTIONS, FEATURE_NAMES, build_feature_row
from app.prediction.predictor import get_metadata, predict_category
from app.preprocessing.pipeline import build_dataframe, impute_raw
from app.training.retrain import retrain
from app.training.train import run_experiment
from app.preprocessing.validation import validate_raw, validate_features
import pandas as pd

app = FastAPI(title="Wellness ML Service", version="1.0.0")


class PredictRequest(BaseModel):
    features: dict = Field(default_factory=dict)
    raw: dict | None = None


class TrainRequest(BaseModel):
    samples: int = Field(default=3000, ge=100, le=100000)


class RetrainRequest(BaseModel):
    extra_rows: list[dict] = Field(default_factory=list)
    extra_labels: list[str] = Field(default_factory=list)
    samples: int = Field(default=3000, ge=100, le=100000)
    force: bool = False


def require_training_admin(x_ml_admin_token: str | None = Header(default=None)):
    expected = os.getenv("ML_ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Training API is disabled; configure ML_ADMIN_TOKEN or use the offline CLI")
    if not x_ml_admin_token or not secrets.compare_digest(x_ml_admin_token, expected):
        raise HTTPException(403, "Training administrator authorization required")


@app.get("/health")
def health():
    return {"success": True, "ml_enabled": ML_ENABLED, "port": ML_PORT}


@app.post("/predict")
def predict(body: PredictRequest):
    features = body.features
    if body.raw is not None:
        try:
            validate_raw(body.raw)
            features = build_feature_row(impute_raw(body.raw))
        except (ValueError, TypeError, KeyError):
            return {"available": False, "reason": "Invalid raw input; check required fields, types, categories and application bounds."}
    if not features:
        return {"available": False, "reason": "No features provided."}
    missing = [name for name in FEATURE_NAMES if name not in features]
    if missing:
        return {"available": False, "reason": f"Invalid input: missing features {missing}"}
    try:
        validate_features(pd.DataFrame([features]))
    except (ValueError, TypeError):
        return {"available": False, "reason": "Invalid features; check finite numeric values, codes and application bounds."}
    return predict_category(features)


@app.get("/model/explanation")
@app.get("/model/metadata")
def metadata():
    data = get_metadata() or {}
    if not data:
        return {"available": False, "reason": "Model metadata is not loaded."}
    return {**data, "available": True, "feature_descriptions": FEATURE_DESCRIPTIONS}


@app.post("/train", dependencies=[Depends(require_training_admin)])
def train_endpoint(body: TrainRequest):
    dataset = os.getenv("ML_TRAINING_DATASET")
    benchmark = os.getenv("ML_BENCHMARK_DATASET")
    if not dataset or not benchmark:
        raise HTTPException(503, "Configure ML_TRAINING_DATASET and ML_BENCHMARK_DATASET")
    output = ROOT / "models" / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    try:
        meta = run_experiment(dataset, benchmark, output, int(os.getenv("ML_TRAINING_SEED", "42")))
    except (ValueError, OSError):
        raise HTTPException(422, "Training dataset validation failed; inspect the configured files") from None
    return {"available": True, "metrics": meta["metrics"], "n_samples": meta["n_samples"], "model_type": meta["model_type"]}


@app.post("/retrain", dependencies=[Depends(require_training_admin)])
def retrain_endpoint(body: RetrainRequest):
    return retrain(body.extra_rows, body.extra_labels, samples=body.samples, force=body.force)


@app.post("/evaluate", dependencies=[Depends(require_training_admin)])
def evaluate_endpoint(body: TrainRequest):
    from app.training.evaluate import evaluate_saved
    try:
        return evaluate_saved()
    except (ValueError, OSError):
        return {"available": False, "reason": "Loaded artifact has no verifiable frozen test split; use the offline experiment CLI."}
