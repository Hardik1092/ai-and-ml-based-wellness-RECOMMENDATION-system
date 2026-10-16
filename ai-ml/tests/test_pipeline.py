import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.features.engineering import FEATURE_NAMES
from app.preprocessing.pipeline import build_dataframe
from app.preprocessing.validation import TARGET, assert_disjoint, load_feature_dataset, validate_features
from app.training.dataset import generate_dataset
from app.training.train import run_experiment, save, split_indices
from app.training.evaluate import evaluate_saved
from app.evaluation.benchmark import parse_output, safety_flags, gemini_request, run as benchmark_run
from app.prediction import predictor


@pytest.fixture(scope="module")
def experiment(tmp_path_factory):
    directory = tmp_path_factory.mktemp("experiment")
    rows, labels = generate_dataset(600, seed=9)
    frame = build_dataframe(rows)
    frame[TARGET] = labels
    path = directory / "features.csv"
    frame.to_csv(path, index=False)
    b_rows, b_labels = generate_dataset(30, seed=1234)
    bench = pd.DataFrame(b_rows)
    bench[TARGET] = b_labels
    benchmark = directory / "benchmark.csv"
    bench.to_csv(benchmark, index=False)
    output = directory / "run"
    meta = run_experiment(path, benchmark, output)
    return directory, path, benchmark, output, meta


@pytest.mark.parametrize("change", ["missing", "unknown_label", "duplicate", "nan", "infinite", "bad_code", "string"])
def test_invalid_datasets(tmp_path, change):
    rows, labels = generate_dataset(600)
    frame = build_dataframe(rows)
    frame[TARGET] = labels
    if change == "missing": frame = frame.drop(columns="age")
    if change == "unknown_label": frame.loc[0, TARGET] = "invented"
    if change == "duplicate": frame = pd.concat([frame, frame.iloc[:1]])
    if change == "nan": frame.loc[0, "bmi"] = np.nan
    if change == "infinite": frame.loc[0, "bmi"] = np.inf
    if change == "bad_code": frame.loc[0, "goal_code"] = 99
    if change == "string": frame["bmi"] = "invalid"
    path = tmp_path / "invalid.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError): load_feature_dataset(path)


def test_missing_dataset_no_fallback(tmp_path):
    with pytest.raises(FileNotFoundError): load_feature_dataset(tmp_path / "absent.csv")


def test_order_and_leakage(experiment):
    _, path, _, _, _ = experiment
    x, y = load_feature_dataset(path)
    assert list(validate_features(x[list(reversed(FEATURE_NAMES))]).columns) == FEATURE_NAMES
    a, b = split_indices(y), split_indices(y)
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert len(set(a['train']) & set(a['test'])) == 0
    assert_disjoint(x.iloc[a['train']], x.iloc[a['test']])
    with pytest.raises(ValueError, match="leakage"): assert_disjoint(x, x.iloc[:1])


def test_serialization_frozen_evaluation_and_backup(experiment):
    _, path, _, out, meta = experiment
    result = evaluate_saved(out / "model.pkl", out / "feature_metadata.json")
    assert result["metrics"] == meta["metrics"]
    model = joblib.load(out / "model.pkl")
    x, _ = load_feature_dataset(path)
    assert set(model.predict(x.iloc[:4])) <= set(meta["classes"])
    backup_dir = out / 'backup-test'
    save(model, meta, backup_dir / 'model.pkl', backup_dir / 'metadata.json')
    original = (backup_dir / 'model.pkl').read_bytes()
    save(model, meta, backup_dir / 'model.pkl', backup_dir / 'metadata.json')
    assert next(backup_dir.glob('model.pkl.*.bak')).read_bytes() == original


def test_loaded_prediction_contract(experiment, monkeypatch):
    _, path, _, out, _ = experiment
    monkeypatch.setattr(predictor, 'MODEL_PATH', out / 'model.pkl')
    monkeypatch.setattr(predictor, 'METADATA_PATH', out / 'feature_metadata.json')
    predictor.reset_cache()
    features = load_feature_dataset(path)[0].iloc[0].to_dict()
    result = TestClient(app).post('/predict', json={'features': features})
    assert result.status_code == 200
    body = result.json()
    assert body['available'] is True
    assert body['category_label'] == body['categoryLabel']
    assert abs(sum(body['probabilities'].values()) - 1) < .001
    predictor.reset_cache()


@pytest.mark.parametrize('raw', [{}, {'age': 25, 'bmi': 'nan'}, {'age': 25, 'bmi': 22, 'water_target_ml': 0}, {'age': -1, 'bmi': 22}, {'age': True, 'bmi': 22}, {'age': 25, 'bmi': 22, 'goal': 'unknown'}, {'age': 25, 'bmi': 22, 'sleep_hours': 24, 'exercise_minutes': 30}])
def test_invalid_raw_api(raw):
    response = TestClient(app).post('/predict', json={'raw': raw})
    assert response.status_code == 200
    assert response.json()['available'] is False


def test_api_auth_and_error_handling(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv('ML_ADMIN_TOKEN', raising=False)
    for endpoint in ('train', 'retrain', 'evaluate'):
        assert client.post('/'+endpoint, json={}).status_code == 503
    monkeypatch.setenv('ML_ADMIN_TOKEN', 'test-only-token')
    for endpoint in ('train', 'retrain', 'evaluate'):
        assert client.post('/'+endpoint, json={}).status_code == 403
    assert client.post('/train', json={}, headers={'X-ML-Admin-Token': 'wrong'}).status_code == 403
    assert client.post('/retrain', json={}, headers={'X-ML-Admin-Token': 'test-only-token'}).json()['promoted'] is False
    monkeypatch.delenv('ML_TRAINING_DATASET', raising=False)
    assert client.post('/train', json={}, headers={'X-ML-Admin-Token': 'test-only-token'}).status_code == 503
    assert client.post('/predict', json={'features': []}).status_code == 422


def test_unavailable_model(monkeypatch, tmp_path):
    monkeypatch.setattr(predictor, 'MODEL_PATH', tmp_path / 'missing.pkl')
    predictor.reset_cache()
    result = predictor.predict_category(build_dataframe(generate_dataset(1)[0]).iloc[0].to_dict())
    assert result['available'] is False
    predictor.reset_cache()


def test_llm_parse_and_unsafe_response():
    good = {'category': 'sleep_focus', 'rationale': 'Synthetic sleep focus.', 'suggestions': ['Keep a regular bedtime.']}
    assert parse_output(json.dumps(good)) == good
    for bad in ('not json', '{}', json.dumps({**good, 'category': 'diagnosis'}), json.dumps({**good, 'extra': 1}), json.dumps({**good, 'suggestions': []})):
        with pytest.raises(ValueError): parse_output(bad)
    assert safety_flags({**good, 'suggestions': ['Stop your medication.']}) == ['medication_change']


def test_llm_provider_failure_and_benchmark_separation(experiment):
    class Response:
        status_code = 404
        def json(self): return {'error': {'message': 'Model unavailable'}}
    class Client:
        def post(self, *args, **kwargs): return Response()
    assert gemini_request(Client(), 'test-model', 'not-a-secret', {}) == {'status': 'provider_error', 'http_status': 404, 'error': {'message': 'Model unavailable'}}
    directory, path, benchmark, out, _ = experiment
    report = benchmark_run(out, benchmark, directory / 'benchmark-output')
    assert report['llm']['attempted'] == 0
    assert report['llm']['valid_only_metrics'] is None
    assert len((directory / 'benchmark-output/outputs.jsonl').read_text().splitlines()) == 30
    with pytest.raises(ValueError, match='already exists'):
        run_experiment(path, benchmark, out)


def test_python_backend_feature_parity():
    import subprocess
    rows, _ = generate_dataset(20, seed=89)
    script = "const fs=require('fs'); const {buildFeatureRow,imputeRaw}=require('./backend/src/services/featureBuilder'); console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(r=>buildFeatureRow(imputeRaw(r)))));"
    result = subprocess.run(['node', '-e', script], input=json.dumps(rows), text=True,
                            capture_output=True, check=True, cwd=Path(__file__).resolve().parents[2])
    expected = build_dataframe(rows)
    actual = pd.DataFrame(json.loads(result.stdout))[FEATURE_NAMES]
    assert np.allclose(actual, expected, atol=1e-9)


def test_saved_project_artifact_and_extreme_inputs(monkeypatch):
    out = Path(__file__).resolve().parents[1] / 'models/cep-20k-v1'
    if not (out / 'model.pkl').exists():
        pytest.skip('Local experiment artifact is not distributed with every checkout')
    monkeypatch.setattr(predictor, 'MODEL_PATH', out / 'model.pkl')
    monkeypatch.setattr(predictor, 'METADATA_PATH', out / 'feature_metadata.json')
    predictor.reset_cache()
    client = TestClient(app)
    for raw in ({'bmi': 10.59, 'age': 16, 'sleep_hours': 3},
                {'bmi': 55.1, 'age': 69, 'sleep_hours': 10},
                {'bmi': 22, 'age': 25, 'sleep_hours': 0, 'water_ml': 0, 'steps': 0},
                {'bmi': 22, 'age': 25, 'sleep_hours': 8, 'water_ml': 10000, 'steps': 100000, 'exercise_minutes': 120}):
        result = client.post('/predict', json={'raw': raw}).json()
        assert result['available'] is True
        assert result['model_type'] == 'HistGradientBoostingClassifier'
        assert np.isfinite(result['confidence'])
    predictor.reset_cache()


def test_modified_split_is_rejected(experiment, tmp_path):
    import shutil
    _, _, _, out, _ = experiment
    copy = tmp_path / 'tampered'
    shutil.copytree(out, copy)
    (copy / 'splits.csv').write_text('row_index,split\n0,test\n')
    with pytest.raises(ValueError, match='hash changed'):
        evaluate_saved(copy / 'model.pkl', copy / 'feature_metadata.json')
