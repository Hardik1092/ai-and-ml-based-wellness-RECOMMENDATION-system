"""Read-only provider diagnosis. Never edits application configuration or prints keys."""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
API = 'https://generativelanguage.googleapis.com/v1beta'


def configuration():
    values = dotenv_values(ROOT / 'backend/.env')
    return (os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY') or '',
            os.environ.get('GEMINI_MODEL') or values.get('GEMINI_MODEL') or 'gemini-1.5-flash')


def redact(value, key):
    text = json.dumps(value)
    if key:
        text = text.replace(key, '[REDACTED]')
    text = re.sub(r'AIza[0-9A-Za-z_-]{20,}', '[REDACTED]', text)
    return json.loads(text)


def diagnose(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new diagnostic output file')
    key, model = configuration()
    protected = [p for p in (ROOT / 'backend/.env', ROOT / 'ai-ml/.env',
                 ROOT / 'backend/src/config/env.js', ROOT / 'ai-ml/app/config.py') if p.exists()]
    report = {'date_utc': datetime.now(timezone.utc).isoformat(), 'api_version': 'v1beta',
              'configured_model': model, 'credential_present': bool(key),
              'configuration_hashes_before': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}}
    if not key:
        report['blocker'] = 'GEMINI_API_KEY is absent from process environment and backend/.env'
    else:
        try:
            with httpx.Client(timeout=30, headers={'x-goog-api-key': key}) as client:
                r = client.post(f'{API}/models/{model}:generateContent', json={
                    'contents': [{'parts': [{'text': 'Reply with OK.'}]}],
                    'generationConfig': {'temperature': 0, 'maxOutputTokens': 16}})
                report['configured_model_probe'] = {'http_status': r.status_code, 'body': redact(r.json(), key)}
                models, token = [], None
                while True:
                    r = client.get(f'{API}/models', params={'pageSize': 100, **({'pageToken': token} if token else {})})
                    if r.status_code != 200:
                        report['model_listing_error'] = {'http_status': r.status_code, 'body': redact(r.json(), key)}
                        break
                    data = r.json()
                    models.extend({k: item.get(k) for k in ('name','version','displayName','supportedGenerationMethods','inputTokenLimit','outputTokenLimit')} for item in data.get('models', []))
                    token = data.get('nextPageToken')
                    if not token:
                        break
                report['models'] = models
        except httpx.RequestError as exc:
            report['blocker'] = type(exc).__name__  # No exception URL/header leakage.
    report['configuration_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p,digest in report['configuration_hashes_before'].items())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    diagnose(args.output)
