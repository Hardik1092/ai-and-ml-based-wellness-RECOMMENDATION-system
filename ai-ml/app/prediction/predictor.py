import json
import logging
import threading
import hashlib
import sklearn

import joblib
import pandas as pd

from app.config import METADATA_PATH, ML_ENABLED, MODEL_PATH
from app.features.engineering import FEATURE_NAMES
from app.utils.constants import CATEGORY_LABELS
from app.preprocessing.validation import validate_features

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_state = {"model": None, "metadata": None, "error": None}

CATEGORY_EXPLANATIONS = {
    "weight_management": "your body-status and calorie-related features dominate your profile",
    "fitness_improvement": "your goal and training-related features dominate your profile",
    "hydration_focus": "your hydration ratio is the weakest signal in your profile",
    "sleep_focus": "your sleep hours are the weakest signal in your profile",
    "activity_focus": "your step count and exercise minutes are the weakest signals",
    "balanced_wellness": "no single area stands out as needing attention",
}


def load_model(force: bool = False):
    with _lock:
        if _state["model"] is not None and not force:
            return _state["model"], _state["metadata"]
        try:
            target_path = MODEL_PATH
            if not target_path.exists():
                fallback_joblib = target_path.parent / "random_forest_model.joblib"
                if fallback_joblib.exists():
                    target_path = fallback_joblib
                else:
                    raise FileNotFoundError(f"model file not found at {MODEL_PATH}")
            metadata = {}
            if METADATA_PATH.exists():
                metadata = json.loads(METADATA_PATH.read_text())
            if metadata.get("features", FEATURE_NAMES) != FEATURE_NAMES:
                raise ValueError("Artifact feature contract mismatch")
            if metadata.get("versions", {}).get("scikit-learn", sklearn.__version__) != sklearn.__version__:
                raise ValueError("Artifact scikit-learn version mismatch")
            if metadata.get("model_sha256") and hashlib.sha256(target_path.read_bytes()).hexdigest() != metadata["model_sha256"]:
                raise ValueError("Artifact checksum mismatch")
            model = joblib.load(target_path)
            if list(model.feature_names_in_) != FEATURE_NAMES or not set(model.classes_).issubset(CATEGORY_LABELS):
                raise ValueError("Model feature or category contract mismatch")
            _state.update({"model": model, "metadata": metadata, "error": None})
            return model, metadata
        except Exception as exc:  # noqa: BLE001
            _state.update({"model": None, "metadata": None, "error": str(exc)})
            logger.warning("ML model unavailable (%s).", exc)
            return None, None


def reset_cache() -> None:
    with _lock:
        _state.update({"model": None, "metadata": None, "error": None})


def get_metadata() -> dict | None:
    _, metadata = load_model()
    return metadata


def predict_category(features: dict, enabled: bool = ML_ENABLED) -> dict:
    if not enabled:
        return {"available": False, "reason": "ML is disabled by configuration (ML_ENABLED=false)."}
    model, metadata = load_model()
    if model is None:
        return {"available": False, "reason": "Model file could not be loaded; using rule-based output."}
    try:
        frame = validate_features(pd.DataFrame([features]))
        category = str(model.predict(frame)[0])
        probabilities = {}
        confidence = None
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(frame)[0]
            probabilities = {str(c): round(float(p), 4) for c, p in zip(model.classes_, proba)}
            confidence = round(float(max(proba)), 4)
        importances = (metadata or {}).get("feature_importances", {})
        top = sorted(importances.items(), key=lambda kv: -kv[1])[:4]
        label = CATEGORY_LABELS.get(category, category.replace("_", " ").title())
        return {
            "available": True,
            "category": category,
            "categoryLabel": label,
            "category_label": label,
            "confidence": confidence,
            "probabilities": probabilities,
            "topFeatures": [{"feature": n, "importance": v} for n, v in top],
            "top_features": [{"feature": n, "importance": v} for n, v in top],
            "explanation": (
                f"The model assigned the synthetic focus category '{category.replace('_', ' ')}'. "
                + ("Global feature importances (not an explanation of this individual prediction): "
                   + ", ".join(name for name, _ in top) + ". " if top else "")
                + "Model probabilities are not clinical confidence. This is general wellness guidance, not a diagnosis."
            ),
            "modelType": (metadata or {}).get("model_type", "RandomForestClassifier"),
            "model_type": (metadata or {}).get("model_type", "RandomForestClassifier"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("ML prediction failed: %s", exc)
        return {"available": False, "reason": "Prediction failed; using rule-based output."}
