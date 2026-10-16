"""Verify the saved experiment and benchmark before any model/provider prediction."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from app.features.engineering import FEATURE_NAMES
from app.preprocessing.pipeline import build_dataframe
from app.preprocessing.validation import TARGET, assert_disjoint, load_feature_dataset, validate_features, validate_raw
from app.training.train import split_indices
from app.training.validate_dataset import overlap


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(run_dir, benchmark):
    run_dir, benchmark = Path(run_dir).resolve(), Path(benchmark).resolve()
    meta = json.loads((run_dir / 'feature_metadata.json').read_text())
    dataset = Path(meta['dataset']['path'])
    for path, expected in ((run_dir/'model.pkl', meta['model_sha256']),
                           (run_dir/'splits.csv', meta['splits_sha256']),
                           (dataset, meta['dataset']['sha256']),
                           (benchmark, meta['benchmark']['sha256'])):
        if sha256(path) != expected:
            raise ValueError(f'Provenance hash mismatch: {path.name}')
    if meta['versions']['scikit-learn'] != sklearn.__version__ or meta['features'] != FEATURE_NAMES:
        raise ValueError('Artifact version or feature contract mismatch')
    X, y = load_feature_dataset(dataset)
    splits = pd.read_csv(run_dir/'splits.csv')
    if len(splits) != len(X) or sorted(splits.row_index.tolist()) != list(range(len(X))):
        raise ValueError('Split membership must cover every source row exactly once')
    reproduced = split_indices(y, meta['seed'])
    counts = {}
    for name, ids in reproduced.items():
        saved = splits.loc[splits.split == name, 'row_index'].to_numpy()
        if not np.array_equal(sorted(saved), sorted(ids)):
            raise ValueError('Saved split does not reproduce the documented seed')
        counts[name] = len(saved)
    expected_profile_hashes = [hashlib.sha256(row.astype(float).to_numpy().tobytes()).hexdigest() for _,row in X.iterrows()]
    if splits.sort_values('row_index').profile_sha256.tolist() != expected_profile_hashes:
        raise ValueError('Split profile hashes mismatch')
    raw = pd.read_csv(benchmark)
    if TARGET not in raw or raw[TARGET].isna().any() or not raw[TARGET].isin(meta['classes']).all():
        raise ValueError('Invalid benchmark labels')
    for row in raw.to_dict('records'):
        validate_raw(row)
    bx = validate_features(build_dataframe(raw.to_dict('records')))
    assert_disjoint(X, bx)
    if bx.duplicated().any():
        raise ValueError('Duplicate benchmark profiles')
    overlaps = {name: overlap(X.iloc[ids], bx) for name,ids in reproduced.items()}
    if any(value['near_including_exact'] for value in overlaps.values()):
        raise ValueError('Benchmark contains defined near-duplicate development/test profiles')
    experiment = json.loads((run_dir/'experiment.json').read_text())
    selected = max(experiment['candidates'], key=lambda name: experiment['candidates'][name]['validation_metrics']['macro_f1'])
    if selected != meta['selected_candidate'] or selected != experiment['selected']:
        raise ValueError('Saved selection differs from validation-only selection rule')
    report = {'model_path': str(run_dir/'model.pkl'), 'model_sha256': sha256(run_dir/'model.pkl'),
              'metadata_sha256': sha256(run_dir/'feature_metadata.json'), 'dataset_sha256': sha256(dataset),
              'splits_sha256': sha256(run_dir/'splits.csv'), 'benchmark_sha256': sha256(benchmark),
              'benchmark_shape': list(raw.shape), 'benchmark_missing_cells': int(raw.isna().sum().sum()),
              'split_counts': counts, 'benchmark_overlap_by_split': overlaps,
              'selection_reproduced_from_validation_macro_f1': selected,
              'methodology': 'Benchmark features were read only for leakage checks before training; no benchmark fitting or scoring occurs in model selection. Confirmed by recorded splits, experiment and training source inspection.',
              'benchmark_used_for_tuning': False, 'preflight_passed': True}
    return meta, raw, bx, report
