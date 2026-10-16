import itertools
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.features.engineering import build_feature_row
from app.preprocessing.pipeline import impute_raw
from app import main


@pytest.mark.parametrize('key,features', [('sleep_hours', ['sleep_hours', 'sleep_adequacy']), ('water_ml', ['hydration_ratio', 'hydration_adequacy']), ('calories', ['calorie_ratio'])])
def test_observed_zero_survives(key, features):
    raw = dict(bmi=22, age=30, sleep_hours=8, water_ml=3000, calories=2400, water_target_ml=3000, calorie_target=2400)
    raw[key] = 0
    for input_row in (raw, impute_raw(raw)):
        row = build_feature_row(input_row)
        assert all(row[name] == 0 for name in features)


@pytest.mark.parametrize('explicit_null', [False, True])
@pytest.mark.parametrize('personal_targets', [False, True])
def test_missing_defaults(explicit_null, personal_targets):
    raw = dict(bmi=22, age=30)
    if explicit_null:
        raw.update(sleep_hours=None, water_ml=None, calories=None)
    if personal_targets:
        raw.update(water_target_ml=3000, calorie_target=2400)
    filled = impute_raw(raw)
    assert filled['sleep_hours'] == 7
    assert filled['water_ml'] == (3000 if personal_targets else 2500)
    assert filled['calories'] == (2400 if personal_targets else 2000)
    row = build_feature_row(filled)
    assert (row['sleep_hours'], row['hydration_ratio'], row['calorie_ratio']) == (7, 1, 1)


def test_backend_python_parity_for_zero_positive_null_and_absent_values():
    rows = []
    for states in itertools.product(['absent', 'null', 'zero', 'positive'], repeat=3):
        raw = dict(bmi=22, age=30, water_target_ml=3000, calorie_target=2400)
        for key, positive, state in zip(['sleep_hours', 'water_ml', 'calories'], [8, 1500, 1200], states):
            if state != 'absent':
                raw[key] = {'null': None, 'zero': 0, 'positive': positive}[state]
        rows.append(raw)
    script = "const {buildFeatureRow,imputeRaw}=require('./backend/src/services/featureBuilder');const fs=require('fs');console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(r=>buildFeatureRow(imputeRaw(r)))));"
    result = subprocess.run(['node', '-e', script], input=json.dumps(rows), text=True, capture_output=True, check=True, cwd=Path(__file__).resolve().parents[2])
    assert json.loads(result.stdout) == [build_feature_row(impute_raw(row)) for row in rows]


def test_raw_api_preserves_zeros_and_missing_defaults(monkeypatch):
    captured = []
    def capture(features):
        captured.append(features)
        return {'available': True}
    monkeypatch.setattr(main, 'predict_category', capture)
    client = TestClient(main.app)
    for raw in [dict(bmi=22, age=30, sleep_hours=0, water_ml=0, calories=0), dict(bmi=22, age=30)]:
        response = client.post('/predict', json={'raw': raw})
        assert response.status_code == 200 and response.json()['available']
    assert [captured[0][k] for k in ['sleep_hours', 'hydration_ratio', 'calorie_ratio']] == [0, 0, 0]
    assert [captured[1][k] for k in ['sleep_hours', 'hydration_ratio', 'calorie_ratio']] == [7, 1, 1]
