"""Re-evaluate only the saved experiment's frozen test membership."""
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from app.config import MODEL_PATH, METADATA_PATH
from app.evaluation.metrics import evaluate_model
from app.preprocessing.validation import load_feature_dataset


def evaluate_saved(model_path=MODEL_PATH, metadata_path=METADATA_PATH):
    meta = json.loads(Path(metadata_path).read_text())
    if 'dataset' not in meta:
        raise ValueError('Legacy artifact has no frozen dataset provenance')
    for path, key in ((Path(model_path), 'model_sha256'), (Path(model_path).parent / 'splits.csv', 'splits_sha256')):
        if hashlib.sha256(path.read_bytes()).hexdigest() != meta.get(key):
            raise ValueError('Artifact or split hash changed')
    dataset = Path(meta['dataset']['path'])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != meta['dataset']['sha256']:
        raise ValueError('Dataset hash changed')
    X, y = load_feature_dataset(dataset)
    splits = pd.read_csv(Path(model_path).parent / 'splits.csv')
    test = splits.loc[splits.split == 'test', 'row_index'].to_numpy()
    metrics = evaluate_model(joblib.load(model_path), X.iloc[test], y.iloc[test])
    return {'available': True, 'metrics': metrics, 'model_type': meta['model_type'], 'n_samples': len(X)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    directory = Path(args.run_dir)
    print(json.dumps(evaluate_saved(directory / 'model.pkl', directory / 'feature_metadata.json'), indent=2))
