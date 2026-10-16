"""Shared computational input contract, not clinical eligibility thresholds."""
import math
from numbers import Real

import numpy as np
import pandas as pd

from app.features.engineering import FEATURE_NAMES
from app.utils.constants import ACTIVITY_LEVELS, GENDERS, GOALS, ML_CATEGORIES

TARGET = "wellness_category"
# Broad application limits retain existing profile/log ranges. They are not targets.
BOUNDS = {
    "bmi": (4, 400), "age": (10, 100), "activity_score": (1, 4),
    "sleep_hours": (0, 24), "sleep_adequacy": (0, 1),
    "hydration_ratio": (0, 20), "hydration_adequacy": (0, 1),
    "exercise_minutes": (0, 1440), "exercise_adequacy": (0, 1),
    "steps_ratio": (0, 12.5), "calorie_ratio": (0, 20),
    "stress_level": (1, 5), "goal_code": (0, len(GOALS)-1),
    "gender_code": (0, len(GENDERS)-1),
}
DISCRETE = {"age", "activity_score", "sleep_adequacy", "hydration_adequacy",
            "exercise_adequacy", "stress_level", "goal_code", "gender_code"}
RAW_BOUNDS = {"bmi": BOUNDS["bmi"], "age": BOUNDS["age"], "weight_kg": (25, 300),
              "sleep_hours": (0, 24), "water_ml": (0, 10000),
              "water_target_ml": (500, 15000), "exercise_minutes": (0, 1440),
              "steps": (0, 100000), "calories": (0, 20000),
              "calorie_target": (500, 10000), "stress_level": (1, 5)}


def validate_raw(raw):
    for name in ("age", "bmi"):
        if name not in raw or raw[name] is None:
            raise ValueError(f"Missing required raw field: {name}")
    for name, (lo, hi) in RAW_BOUNDS.items():
        value = raw.get(name)
        if value is None:
            continue  # Existing documented defaults apply to optional log fields.
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f"Invalid {name}: expected finite number in [{lo}, {hi}]")
        if name in ("age", "stress_level") and value != int(value):
            raise ValueError(f"Invalid {name}: expected integer")
    for name, allowed in (("gender", GENDERS), ("goal", GOALS), ("activity_level", ACTIVITY_LEVELS)):
        if name in raw and raw[name] not in allowed:
            raise ValueError(f"Invalid {name}")
    if raw.get("sleep_hours") is not None and raw.get("exercise_minutes") is not None:
        if raw["sleep_hours"] * 60 + raw["exercise_minutes"] > 1440:
            raise ValueError("Sleep and exercise cannot exceed 24 hours per day combined")


def validate_features(frame):
    missing = set(FEATURE_NAMES) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing feature columns: {sorted(missing)}")
    frame = frame[FEATURE_NAMES].copy()
    for name, (lo, hi) in BOUNDS.items():
        values = frame[name]
        if not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
            raise ValueError(f"{name} must be numeric")
        if not np.isfinite(values).all() or not values.between(lo, hi).all():
            raise ValueError(f"{name} must be finite and in [{lo}, {hi}]")
        if name in DISCRETE and not (values == values.round()).all():
            raise ValueError(f"{name} must contain integer codes")
    for indicator, source, threshold in (("sleep_adequacy", "sleep_hours", 7),
                                          ("exercise_adequacy", "exercise_minutes", 30)):
        if not (frame[indicator] == (frame[source] >= threshold).astype(int)).all():
            raise ValueError(f"Inconsistent {indicator}")
    # Ratio is rounded to 3 decimals AFTER the indicator is calculated.
    bad = ((frame.hydration_ratio < .8995) & (frame.hydration_adequacy != 0)) | ((frame.hydration_ratio >= .9005) & (frame.hydration_adequacy != 1))
    if bad.any():
        raise ValueError("Inconsistent hydration_adequacy")
    if (frame.sleep_hours * 60 + frame.exercise_minutes > 1440).any():
        raise ValueError("Sleep and exercise exceed the daily time budget")
    return frame


def load_feature_dataset(path):
    frame = pd.read_csv(path)  # Missing paths deliberately fail; no generator fallback.
    if set(frame.columns) != set(FEATURE_NAMES + [TARGET]):
        raise ValueError(f"Dataset must contain exactly {FEATURE_NAMES + [TARGET]}")
    x = validate_features(frame)
    y = frame[TARGET]
    if y.isna().any() or not y.isin(ML_CATEGORIES).all():
        raise ValueError("Unknown or missing wellness_category")
    if set(y) != set(ML_CATEGORIES) or y.value_counts().min() < 5:
        raise ValueError("At least five rows of every category are required for stratification")
    if x.duplicated().any():
        raise ValueError("Duplicate feature profiles require explicit grouping before splitting")
    return x, y


def assert_disjoint(left, right):
    a = set(pd.util.hash_pandas_object(left[FEATURE_NAMES].astype(float), index=False))
    b = set(pd.util.hash_pandas_object(right[FEATURE_NAMES].astype(float), index=False))
    if a & b:
        raise ValueError(f"Data leakage: {len(a & b)} overlapping feature profiles")
