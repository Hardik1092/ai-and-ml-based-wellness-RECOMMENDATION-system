import json

import httpx
import pytest

from app.evaluation import benchmark as bench
from app.evaluation.benchmark_checks import preflight


def client_for(responses):
    pending = iter(responses)
    return httpx.Client(transport=httpx.MockTransport(lambda request: next(pending)))


def test_error_body_redacts_credentials():
    key = 'test-private-key'
    client = client_for([httpx.Response(404, json={'error': {'message': 'invalid '+key}})])
    result = bench.gemini_request(client, 'test', key, {})
    assert result['http_status'] == 404
    assert key not in json.dumps(result)
    assert '[REDACTED]' in result['error']['message']


def test_all_responses_preserve_usage_and_finish_reason():
    body = {'modelVersion': 'version-1', 'usageMetadata': {'promptTokenCount': 20, 'candidatesTokenCount': 3},
            'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{unfinished'}]}}]}
    result = bench.gemini_request(client_for([httpx.Response(200, json=body)]), 'test', 'secret', {})
    assert result['status'] == 'incomplete_or_blocked'
    assert result['raw_output'] == '{unfinished'
    assert result['usage']['candidatesTokenCount'] == 3
    assert result['finish_reason'] == 'MAX_TOKENS'


def test_transient_retries_preserve_first_attempt(monkeypatch):
    output = {'category':'balanced_wellness','rationale':'Synthetic category.','suggestions':['Keep regular habits.']}
    success = {'modelVersion': 'test', 'candidates':[{'finishReason':'STOP', 'content':{'parts':[{'text':json.dumps(output)}]}}]}
    client = client_for([httpx.Response(503,json={'error':{'message':'busy'}}), httpx.Response(200,json=success)])
    monkeypatch.setattr(bench.time, 'sleep', lambda _: None)
    result = bench.request_with_retries(client,'test','key',{},2)
    assert result['status'] == 'ok'
    assert len(result['attempts']) == 2
    assert result['attempts'][0]['http_status'] == 503


def test_invalid_generated_answer_is_never_retried(monkeypatch):
    body = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'not json'}]}}]}
    result = bench.request_with_retries(client_for([httpx.Response(200,json=body)]),'test','key',{},2)
    assert result['status'] == 'invalid_output'
    assert len(result['attempts']) == 1


def test_new_model_omits_ignored_temperature():
    assert 'temperature' not in bench.generation_config('gemini-3.5-flash-lite')
    assert bench.generation_config('gemini-2.5-flash-lite')['temperature'] == 0


def test_original_benchmark_and_artifact_separation():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    run = root/'ai-ml/models/cep-20k-v1'
    if not run.exists():
        pytest.skip('Local experiment artifact unavailable')
    _, raw, features, checks = preflight(run, root/'CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv')
    assert len(raw) == len(features) == 200
    assert checks['split_counts'] == {'train':12000,'validation':4000,'test':4000}
    assert all(v['near_including_exact'] == 0 for v in checks['benchmark_overlap_by_split'].values())


def test_analysis_preserves_failures_and_cost_denominators(tmp_path):
    from app.evaluation.analyze_benchmark import analyze
    output={'category':'sleep_focus','rationale':'Sleep is below the synthetic threshold.','suggestions':['Keep a regular bedtime.']}
    success={'status':'ok','output':output,'raw_output':json.dumps(output),'model_version':'test',
             'usage':{'promptTokenCount':100,'candidatesTokenCount':50,'thoughtsTokenCount':10},
             'http_status':200,'attempt_latency_ms':100}
    failure={'status':'provider_error','http_status':503,'attempt_latency_ms':20}
    features={'sleep_hours':5}
    rows=[{'case_id':'a','features':features,'reference':'sleep_focus','ml':{'category':'sleep_focus','latency_ms':1},
           'rule':{'category':'sleep_focus','latency_ms':.01},'llm':{**success,'attempts':[failure,success],'latency_ms':2120}},
          {'case_id':'b','features':features,'reference':'sleep_focus','ml':{'category':'balanced_wellness','latency_ms':1},
           'rule':{'category':'sleep_focus','latency_ms':.01},'llm':{'status':'invalid_output','raw_output':'bad',
              'attempts':[{'status':'invalid_output','http_status':200,'attempt_latency_ms':100}],'latency_ms':100}}]
    (tmp_path/'outputs.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    (tmp_path/'summary.json').write_text(json.dumps({'cases':2}))
    result=analyze(tmp_path)
    assert result['total_api_attempts']==3
    assert result['schema_valid_rate_all_cases']==.5
    assert result['metrics']['llm']['accuracy']==.5
    assert result['metrics']['llm_first_attempt']['accuracy']==0
    assert result['cost']['estimated_standard_paid_usd_known_usage']==pytest.approx(.00018)
    assert result['cost']['actual_billed_usd'] is None
